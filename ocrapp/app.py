from flask import Flask, request, redirect, url_for, render_template
from flask import send_file, send_from_directory
import os
import json
import glob
from uuid import uuid4
import easyocr
import cv2
import re
import datetime
import xlsxwriter

app = Flask(__name__)

response = []

bank_name_list = [
    {
        'en_name': 'Siam Commercial Bank', 
        'th_name' : 'ธนาคารกรุงเทพ',
        'synonyms': ['scb']
    }, 
    {
        'en_name': 'Bangkok Bank',
        'th_name': 'ธนาคารกรุงเทพ',
        'synonyms': ['bualuang', 'ธนาคารกรุงเทพ', 'bangkok bank']
    }, 
    {
        'en_name': 'Krung Thai Bank',
        'th_name': 'ธนาคารกรุงไทย',
        'synonyms': ['krungthai', 'กรุงไทย']
    },
    {
        'en_name': 'Kasikorn Bank',
        'th_name': 'ธนาคารกสิกรไทย',
        'synonyms': ['ธ.กสิกรไทย']
    },
    {
        'en_name': 'Thanachart Bank',
        'th_name': 'ธนาคารธนชาต',
        'synonyms': ['thanachart Bank', 'ธนาคารธนชาต']
    },
    {
        'en_name': 'Krunsri Bank',
        'th_name': 'ธนาคารธนชาต',
        'synonyms': ['krungsri', 'ธนาคารธนชาต']
    },
    {
        'en_name': 'TMB Bank',
        'th_name': 'ธนาคารทหารไทย จำกัด',
        'synonyms': ['tmb', 'ทีเอ็มบี']
    },
    {
        'en_name': 'Bank for Agriculture and Agricultural Cooperatives',
        'th_name': 'ธนาคารเพื่อการเกษตรและสหกรณ์การเกษตร',
        'synonyms': ['BAAC', 'ธ.ก.ส.']
    }
]

th_en_month = [
        'ม.ค.',
        'ก.พ.',
        'มี.ค.',
        'เม.ย.',
        'พ.ค.',
        'มิ.ย.',
        'ก.ค.',
        'ส.ค.',
        'ก.ย.',
        'ต.ค.',
        'พ.ย.',
        'ธ.ค.'
]
# convert thai month to en month
def convert_month_th2en(th_month):
    for index, th_month in enumerate(th_en_month):
        if th_month in th_month:
            return str(index+1)

# convert thai year to en year
def convert_year_th2en(th_year):
    # if length of year is 2(e.g. 63)
    en_year = 2020
    if len(th_year) == 2:
        en_year = int(th_year) + 1957
    else: # lenth is 4
        en_year = int(th_year) -43
    return str(en_year)

def convert_date_th2en(th_date):
    date_list = th_date.split()
    day = date_list[0]
    th_month = date_list[1]
    th_year = date_list[2]
    en_month = convert_month_th2en(th_month)
    en_year = convert_year_th2en(th_year)

    en_date = datetime.datetime.strptime(day+'/'+en_month+'/'+en_year, "%d/%m/%Y").strftime('%d/%m/%Y') 
    return en_date

def check_date_format(date):
    try:
        parse(date, dayfirst=True)
        return 'en'
    except ValueError:
        try:
            parse(date)
            return 'en'
        except ValueError:
            return 'th'

def find_candidate(result, entry, regex):
    candidate = ''
    exists = False
    top_left, top_right, bottom_right, bottom_left = entry[0]
    height = bottom_left[1] - top_left[1]
    for entry1 in result:
        top_left1, top_right1, bottom_right1, bottom_left1 = entry1[0]
        # y coordinate should be same or under of label
        if (abs(top_left1[1] - top_left[1]) < height/3 and abs(bottom_left1[1] - bottom_left[1]) < height/2):
            matched = re.search(regex, entry1[1])
            if matched:
                exists = True
                candidate = matched.group(0)
    
    if exists:
        return candidate
    for entry1 in result:
        top_left1, top_right1, bottom_right1, bottom_left1 = entry1[0]
        # y coordinate should be same or under of label
        if (top_left1[1] - top_left[1] < 3 * height and top_left1[1] - top_left[1] > 0):
            matched = re.search(regex, entry1[1])
            if matched:
                candidate = matched.group(0)
    return candidate


def main_process(result):
    amount = ''
    fee = ''
    amount_regex = '[0-9od][0-9,.od]+'
    for entry in result:
        e_text = entry[1]
        # find amount
        if 'จำนวน' in e_text:
            amount = find_candidate(result, entry, amount_regex)
            amount = amount.replace('o', '0').replace('d', '0')
        # if 'ค่าธรรมเนียม' in e_text:
        #     fee = find_candidate(result, entry, amount_regex)
        #     fee = fee.replace('o', '0').replace('d', '0')     
        if 'โอนมินสำเร็จ' in e_text:
            amount = find_candidate(result, entry, amount_regex)
            amount = amount.replace('o', '0').replace('d', '0')
    # find date
    transaction_date = ''
    match_string = '[0-9]{1,2}\s*.\..\.\s*(([0-9]{4})|([0-9]{2}))'
    for entry in result:
        e_text = entry[1]
        try:
            transaction_date = re.search(match_string, e_text).group(0)
            break
        except AttributeError:
            transaction_date = ''
    if not transaction_date:
        match_string = '[0-9]{2}\/[0-9]{2}\/[0-9]{4}'
        for entry in result:
            e_text = entry[1]
            try:
                transaction_date = re.search(match_string, e_text).group(0)
                break
            except AttributeError:
                transaction_date = ''
    # find time
    transaction_time = ''
    match_string = '[0-9]{2}\s*\:\s*[0-9]{2}(\s*\:\s*[0-9]{2})?'
    for entry in result:
        e_text = entry[1]
        try:
            transaction_time = re.search(match_string, e_text).group(0)
            break
        except AttributeError:
            transaction_time = ''
    # find bank name
    bank_name = ''
    
    for entry in result:
        for bank_info in bank_name_list:
            bank_synonyms = bank_info['synonyms']
    #         print(bank_synonyms)
            for bank_synonym in bank_synonyms:
                e_text = entry[1]
                if  bank_synonym in e_text:
                    bank_name = bank_info['en_name']
                    break
    res = {'amount':amount, 'transaction_date':transaction_date, 'transaction_time':transaction_time, 'bank_name': bank_name}
    return res

@app.route("/", methods=['GET', 'POST'])
def index():
    return render_template("index.html")

@app.route("/expert", methods=['GET', 'POST'])
def expert():
    workbook = xlsxwriter.Workbook('./ocrapp/static/uploads/expert.xlsx')
    en_worksheet = workbook.add_worksheet("EN")
    th_worksheet = workbook.add_worksheet("TH")
    workbook.close()
    return json.dumps(dict(
        status=True,
        file='1.xlsx',
    ))
    # return send_from_directory('./', filename='1.xlsx', as_attachment=True)
    # return send_file('2.txt',
    #                  attachment_filename='2.txt',
    #                  as_attachment=True)
@app.route("/upload", methods=["POST"])
def upload():
    response = []
    """Handle the upload of a file."""
    form = request.form

    # Create a unique "session ID" for this particular batch of uploads.
    upload_key = str(uuid4())

    # Is the upload using Ajax, or a direct POST by the form?
    is_ajax = False
    if form.get("__ajax", None) == "true":
        is_ajax = True

    # Target folder for these uploads.
    target = "ocrapp/static/uploads/{}".format(upload_key)
    print('is_ajax', is_ajax)
    try:
        os.mkdir(target)
    except:
        if is_ajax:
            return ajax_response(False, "Couldn't create upload directory: {}".format(target))
        else:
            return "Couldn't create upload directory: {}".format(target)
    files = []
    for upload in request.files.getlist("file"):
        filename = upload.filename.rsplit("/")[0]
        destination = "/".join([target, filename])
        upload.save(destination)
        files.append(destination)
    print(files)
    for file in files:
        image = cv2.imread(file)
        reader = easyocr.Reader(['th','en'], gpu=False) # need to run only once to load model into memory
        result = reader.readtext(image, width_ths=0.7)
        result = main_process(result)
        filename = file.rsplit("/")[-1]
        response.append({'file':filename, 'info':result})
    print(response)
    if is_ajax:
        return ajax_response(True, upload_key)
    else:
        return redirect(url_for("upload_complete", uuid=upload_key))


@app.route("/files/<uuid>")
def upload_complete(uuid):
    """The location we send them to at the end of the upload."""

    # Get their files.
    root = "ocrapp/static/uploads/{}".format(uuid)
    if not os.path.isdir(root):
        return "Error: UUID not found!"

    files = []
    for file in glob.glob("{}/*.*".format(root)):
        fname = file.split(os.sep)[-1]
        files.append(fname)
    print(files)
    return render_template("index.html",
        uuid=uuid,
        files=files,
    )


def ajax_response(status, msg):
    status_code = "ok" if status else "error"
    return json.dumps(dict(
        status=status_code,
        msg=msg,
    ))

