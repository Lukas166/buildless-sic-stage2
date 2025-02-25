from flask import Flask, request, jsonify
from pymongo import MongoClient
import certifi
from datetime import datetime

app = Flask(__name__)

# MongoDB Atlas connection
MONGO_URI = "mongodb+srv://lukasaustin16:lukaslukas@buildless.ev4l8.mongodb.net/?retryWrites=true&w=majority&appName=Buildless"
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["Buildless"]
collection = db["Test"]

@app.route('/data', methods=['POST'])
def receive_data():
    try:
        # Ambil data dari request
        data = request.json
        data["timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        result = collection.insert_one(data)
        print("Data berhasil dikirim ke MongoDB!")
        print("ID dokumen yang disisipkan:", result.inserted_id)

        return jsonify({"status": "success", "message": "Data received and stored in MongoDB"}), 200
    except Exception as e:
        print("Gagal mengirim data ke MongoDB:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)