from flask import render_template, redirect, url_for, request, session
from user import app

import tempfile
import os
import boto3

from wand.image import Image

from user import db


@app.route('/imagetransform/form', methods=['GET'])
# Return file upload form
def image_form():
    if 'username' not in session:
        return "you must be logged in to do that"
    return render_template("imagetransform/form.html",
                           page_header="Upload Image")


@app.route('/imagetransform', methods=['POST'])
# Upload a new image and tranform it
def image_transform():
    if 'username' not in session:
        return "you must be logged in to do that"

    # check if the post request has the file part
    if 'image_file' not in request.files:
        return "Missing uploaded file"

    new_file = request.files['image_file']

    # if user does not select file, browser also
    # submit a empty part without filename
    if new_file.filename == '':
        return 'Missing file name'

    # following line was in the provided code
    # tempdir = tempfile.gettempdir()

    # file is first saved and transformed locally, then it will be uploaded to S2
    fname = os.path.join('user/static', new_file.filename)
    new_file.save(fname)
    img = Image(filename=fname)
    img.save(filename=fname)

    # rotate the image and save
    i1 = img.clone()
    i1.rotate(180)
    fname_rotated = os.path.join('user/static', 'rotated_' + new_file.filename)
    i1.save(filename=fname_rotated)

    # equalize the image and save
    i2 = img.clone()
    i2.equalize()
    fname_equalized = os.path.join('user/static', 'equalized_' + new_file.filename)
    i2.save(filename=fname_equalized)

    # make a negative of the image and save
    i3 = img.clone()
    i3.negate()
    fname_negative = os.path.join('user/static', 'negative_' + new_file.filename)
    i3.save(filename=fname_negative)

    # save files to S3
    s3 = boto3.client('s3')

    folder = session['username'] + "/"

    files = [folder + os.path.basename(fname),
             folder + os.path.basename(fname_rotated),
             folder + os.path.basename(fname_equalized),
             folder + os.path.basename(fname_negative)]


    s3.upload_file(fname,
                   'ece1779assignment1source',
                   files[0])
    s3.upload_file(fname_rotated,
                   'ece1779assignment1source',
                   files[1])
    s3.upload_file(fname_equalized,
                   'ece1779assignment1source',
                   files[2])
    s3.upload_file(fname_negative,
                   'ece1779assignment1source',
                   files[3])

    # save s3 keys to images database
    db.save_images(session['username'], files)

    # delete local copies of image
    for file in [fname, fname_rotated, fname_equalized, fname_negative]:
        os.remove(file)

    # get images from s3
    image_urls = []
    for i in range(len(files)):
        image_urls.append("https://s3.amazonaws.com/ece1779assignment1source/" + files[i])

    # temporarily redirect to page showing image, but should pass the s3 links
    # todo redirect to "show my images" page
    return render_template("imagetransform/view.html",
                           f1=image_urls[0],
                           f2=image_urls[1],
                           f3=image_urls[2],
                           f4=image_urls[3],
                           page_header="Image uploaded")
