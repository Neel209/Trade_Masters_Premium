import uuid
import flask_pymongo as pymongo
import qrcode
from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
from flask_cors import CORS
import traceback
import PIL


# Initialize Flask Application
app = Flask(__name__)
CORS(app) 

# MongoDB Connection
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client['trade_masters']
payments_collection = db['payments']

# Ensure the QR code directory exists
QR_CODE_DIR = "static/qrcodes"
os.makedirs(QR_CODE_DIR, exist_ok=True)

# Define available subscription plans and their corresponding amounts
PLANS = {
    'weekly': 449,
    'monthly': 999,
    'half-yearly': 2999,
    'yearly': 3999,
    'lifetime': 5999
}

# Homepage: Render Subscription Plans
@app.route('/')
def subscription_page():
    return render_template('index.html', plans=PLANS)

# Route to Handle User Input and Save to Database
@app.route('/submit', methods=['POST'])
def submit():
    try:
        # Get data from the request
        data = request.json
        name = data.get("name")
        mobile = data.get("mobile")
        plan = data.get("plan")
        amount = data.get("amount")
        upi_id=data.get("upi_id")
        # Validate data
        if not name or not mobile or not plan or not amount:
            return jsonify({"error": "All fields are required"}), 400
        

        # Generate a unique transaction ID
        transaction_id = str(uuid.uuid4())

        # Generate UPI Payment URL
        upi_id = "Neelrupareliya09@oksbi"
        payment_url = (
            f"upi://pay?pa={upi_id}&pn=Neel Rupareliya&am={amount}&cu=INR&tid={transaction_id}"
            f"&tn=Complete payment and contact @NeelRupareliya on Telegram"
        )

        # Generate QR Code
        qr_code_filename = f"{transaction_id}.png"
        qr_code_path = os.path.join(QR_CODE_DIR, qr_code_filename)
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(payment_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_code_path)

        # Save data to MongoDB
        payment_data = {
            "transaction_id": transaction_id,
            "name": name,
            "mobile": mobile,
            "plan": plan,
            "amount": amount,
            "payment_url": payment_url,
            "qr_code_path": qr_code_path,
            "status": "Pending"
        }
        payments_collection.insert_one(payment_data)

        # Return success response
        return jsonify({
            "message": "Payment data saved successfully",
            "transaction_id": transaction_id
            
        }), 200

    except Exception as e:
        print("Error occurred:", str(e))
        print(traceback.format_exc())  # Print full error details
        return jsonify({"error": "Internal Server Error"}), 500

# Route to Render Payment Confirmation Page
@app.route('/payment_confirmation/<transaction_id>')
def payment_confirmation(transaction_id):
    try:
        # Fetch transaction details from the database
        transaction = payments_collection.find_one({"transaction_id": transaction_id})
        if not transaction:
            return jsonify({"error": "Transaction not found."}), 404

        # Render the payment confirmation page
        return render_template(
            'payment_confirmation.html',
            plan=transaction['plan'],
            amount=transaction['amount'],
            qr_code_filename=os.path.basename(transaction['qr_code_path']),
            telegram_username="NeelRupareliya",
            transaction_id=transaction_id
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route for Payment Confirmation (Mark Payment as Completed)
@app.route('/confirm_payment/<transaction_id>', methods=['POST'])
def confirm_payment(transaction_id):
    try:
        # Simulate Payment Status Update (marking payment as completed)
        result = payments_collection.update_one(
            {"transaction_id": transaction_id},
            {"$set": {"status": "Completed"}}
        )

        if result.modified_count > 0:
            return jsonify({"message": "Payment successful!", "transaction_id": transaction_id})
        else:
            return jsonify({"message": "Transaction not found or already completed."}), 404

    except Exception as e:
        print("Error occurred:", str(e))
        print(traceback.format_exc())  # Print full error details
        return jsonify({"error": "Internal Server Error"}), 500

# Route to View All Transactions (for debugging or admin purposes)
@app.route('/transactions')
def view_transactions():
    try:
        transactions = list(payments_collection.find({}, {"_id": 0}))
        return jsonify(transactions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(port=8000, host='0.0.0.0', debug=True)