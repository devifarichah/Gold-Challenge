from flask import request
from flasgger import Swagger, LazyString, LazyJSONEncoder
from flasgger import swag_from

import re
import pandas as pd
import sqlite3
import os

from flask import Flask, jsonify

app = Flask(__name__)

app.json_encoder = LazyJSONEncoder
swagger_template = dict(
info = {
	'title': LazyString(lambda: 'API Documentation for Data Processing and Modeling'),
	'version': LazyString(lambda: '1.0.0'),
	'description': LazyString(lambda: 'Gold Challenge - Dokumentasi API untuk Data Processing dan Modeling'),
	},
	host = LazyString(lambda: request.host)
)
swagger_config = {
	"headers": [],
	"specs": [
		{
			"endpoint": 'docs',
			"route": '/docs.json',
		}
	],
	"static_url_path": "/flasgger_static",
	"swagger_ui": True,
	"specs_route": "/docs/"
}
swagger = Swagger(app, template=swagger_template,             
				  config=swagger_config)

@swag_from("docs/text.yml", methods=['GET'])
@app.route('/text', methods=['GET'])
def text():
	json_response = {
		'status_code': 200,
		'description': "Original Teks",
		'data': "Halo, apa kabar semua?",
	}

	response_data = jsonify(json_response)
	return response_data

# File CSV
df = pd.read_csv('new_kamusalay.csv', encoding = 'latin-1',names=['Informal', 'Formal'])

# Membuat tabel hasil cleansing text
# conn.execute('''CREATE TABLE Dokumentasi_Text_Cleansing (Clean_Text varchar(255));''')

# Mengganti kata dari kamus alay
kamusalay = dict(zip(df['Informal'], df['Formal']))
def clean_dict(text):
	words = text.split()
	text_informal = [kamusalay.get(x,x) for x in words]
	clean_informal = ' '.join(text_informal)
	return clean_informal

# Function untuk membersihkan data
def cleansing_text(text):
	# Menghilangkan emoji
	text = re.sub(r'\\x\w{2}|\\x\w\d|\\x\d{2}|\\x\\d\w|\\x\d', ' ', text)
	text = re.sub(r'\\ud\d{2}\w|\\ud\w\d{2}', ' ', text)
	# Merubah angka menjadi huruf
	text = re.sub(r'1', ' satu ', text)
	text = re.sub(r'2', ' dua ', text)
	text = re.sub(r'3', ' tiga ', text)
	text = re.sub(r'4', ' empat ', text)
	text = re.sub(r'5', ' lima ', text)
	text = re.sub(r'6', ' enam ', text)
	text = re.sub(r'7', ' tujuh ', text)
	text = re.sub(r'8', ' delapan ', text)
	text = re.sub(r'9', ' sembilan ', text)
	text = re.sub(r'0', ' nol ', text)
	# Menghilangkan kata USER dan RT USER
	text = re.sub(r'USER\W+|RT\sUSER|USER$', ' ', text)
	# Mengilangkan kata URL
	text = re.sub(r'URL\s|URL$', ' ', text)
	# menghilangkan alamat website
	text = re.sub(r'https?:\S+|www.\S+', ' ', text) 
	# Menghapus karakter yang berulang > 2 kali
	text = re.sub(r'([a-zA-Z])\1{2,}', r'\1', text)
	# Menghapus kata yang hanya memiliki 1 huruf
	text = ' '.join([i for i in text.split() if len(i) > 1])
	# Menghilangkan new line dan tabs
	text = re.sub(r'\\n|\\t|\\u', ' ', text)
	# Menghilangkan @username
	text = re.sub(r'@\S+', '', text)
	# Menghilangkan #
	text = re.sub(r'#\S+', ' ', text) 
	# Menghilangkan % dan $ yang tidak memiliki konteks
	text = re.sub(r'\W\s?\%|\W\s?\$', ' ', text)
	# Merubah % menjadi 'persen'
	text = re.sub(r'\%', ' persen ', text) 
	# Merubah $ menjadi 'Dollar'
	text = re.sub(r'\$', ' Dollar ', text)
	# Mengilangkan & dan &amp;
	text = re.sub(r'&\s|&amp;', 'dan', text)
	# Mengilangkan &lt; dan &gt;
	text = re.sub(r'&lt;|&gt;', ' ', text) 
	# Mengilangkan tanda '=' > 1
	text = re.sub(r'\={2,}', ' ', text)  
	# Merubah = menjadi 'sama dengan'
	text = re.sub(r'\=', ' sama dengan ', text)
	# Merubah +62 menjadi 0 pada nomor telepon
	text = re.sub(r'\+62', ' 0', text)
	# Menghilangkan seluruh tanda baca
	text = re.sub(r'[^a-zA-Z0-9]+', ' ',text)
	# Menampilkan satu spasi antar kata
	text = re.sub(r'\s+', ' ', text)
	# Menghapus spasi di awal kalimat
	text = re.sub(r'^\s+|\s+$', '', text)
	# Lowercase text
	text = text.lower()
	return text

# Function untuk text cleansing
def preprocessing_text(text):
	text = clean_dict(text)
	text = cleansing_text(text)
	return text

@swag_from("docs/text_processing.yml", methods=['POST'])
@app.route('/text-processing', methods=['POST'])
def text_processing():

	text = request.form.get('text')
	
	# Hasil text cleansing
	output = preprocessing_text(text)

	# Membuat database jika belum ada
	if not os.path.exists('data'):
		os.makedirs('data')

	# Menambahkan hasil text cleansing ke database
	conn = sqlite3.connect('data/Gold_Challenge.db')
	conn.execute('''CREATE TABLE if not exists Dokumentasi_Text_Cleansing (Clean_Text varchar(255));''')
	conn.execute('INSERT INTO Dokumentasi_Text_Cleansing VALUES (?)', (output,))
	conn.commit()
	conn.close()

	json_response = {
		'status_code': 200,
		'description': "Teks yang sudah diproses",
		'data': preprocessing_text(text),
	}

	response_data = jsonify(json_response)
	return response_data

@swag_from("docs/text_processing_file.yml", methods=['POST'])
@app.route('/text-processing-file', methods=['POST'])
def text_processing_file():

	# Upladed file
	file = request.files.getlist('file')[0]

	# Import file csv ke Pandas
	df = pd.read_csv(file, encoding = 'latin-1')
	assert df.columns == 'text'

	# Ambil teks yang akan diproses dalam format list
	texts = df['text'].to_list()

	# Lakukan cleansing pada teks
	cleaned_text = []
	for text in texts:
		cleaned_text.append(preprocessing_text(text))

	# Hasil text cleansing
	output_file = cleaned_text

	for output in output_file:
		# Membuat database jika belum ada
		if not os.path.exists('data'):
			os.makedirs('data')
		# Menambahkan hasil text cleansing ke database
		conn = sqlite3.connect('data/Gold_Challenge.db')
		conn.execute('''CREATE TABLE if not exists Dokumentasi_Text_Cleansing (Clean_Text varchar(255));''')
		conn.execute('INSERT INTO Dokumentasi_Text_Cleansing VALUES (?)', (output,))
		conn.commit()
		conn.close()
		
	json_response = {
		'status_code': 200,
		'description': "Teks yang sudah diproses",
		'data': cleaned_text,
	}

	response_data = jsonify(json_response)
	return response_data

if __name__ == '__main__':
	app.run()
