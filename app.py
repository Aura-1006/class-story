from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, flash
from werkzeug.utils import secure_filename
import os
import uuid
from PIL import Image
from flask_wtf import CSRFProtect

app = Flask(__name__)
app.secret_key = "change-this-secret"
csrf = CSRFProtect(app)

UPLOAD_FOLDER = "static/uploads/"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB limit
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}

characters = []
stories = []
user_profile = {
    "nicename": "Kullanıcı",
    "bio": "Hoş geldiniz!",
    "profile_image": None,
    "liked_stories": [],
    "liked_characters": []
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file_storage):
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None
    try:
        # Verify and sanitize image using Pillow
        img = Image.open(file_storage.stream)
        img.verify()
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream).convert("RGBA")
        filename = f"{uuid.uuid4().hex}.png"
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        img.save(save_path, format="PNG")
        return filename
    except Exception as e:
        print("Image validation failed:", e)
        return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/characters")
def api_characters():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 8))
    start = (page-1)*per_page
    end = start + per_page
    items = characters[start:end]
    return jsonify({
        "characters": items,
        "page": page,
        "has_more": end < len(characters)
    })


@app.route("/create")
def create():
    return render_template("create.html")


@app.route("/add_character", methods=["GET", "POST"])
def add_character():
    if request.method == "POST":
        name = request.form.get("name")
        bio = request.form.get("bio")
        image_file = request.files.get("image")
        filename = save_image(image_file)
        character = {
            "id": uuid.uuid4().hex,
            "name": name,
            "bio": bio,
            "image": filename
        }
        characters.append(character)
        return redirect(url_for("index"))
    return render_template("add.html", characters=characters)


@app.route("/stories")
def stories_page():
    return render_template("stories.html", stories=stories)


@app.route("/add_story", methods=["GET", "POST"])
def add_story():
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        selected_chars = request.form.getlist("characters")
        story = {
            "id": uuid.uuid4().hex,
            "title": title,
            "content": content,
            "characters": selected_chars
        }
        stories.append(story)
        return redirect(url_for("stories_page"))
    return render_template("add_story.html", characters=characters)


@app.route("/api/like_character/<character_id>", methods=["POST"])
def like_character(character_id):
    global user_profile
    if character_id not in user_profile["liked_characters"]:
        user_profile["liked_characters"].append(character_id)
    return jsonify({"success": True})


@app.route("/api/unlike_character/<character_id>", methods=["POST"])
def unlike_character(character_id):
    global user_profile
    if character_id in user_profile["liked_characters"]:
        user_profile["liked_characters"].remove(character_id)
    return jsonify({"success": True})


@app.route("/api/like_story/<story_id>", methods=["POST"])
def like_story(story_id):
    global user_profile
    if story_id not in user_profile["liked_stories"]:
        user_profile["liked_stories"].append(story_id)
    return jsonify({"success": True})


@app.route("/api/unlike_story/<story_id>", methods=["POST"])
def unlike_story(story_id):
    global user_profile
    if story_id in user_profile["liked_stories"]:
        user_profile["liked_stories"].remove(story_id)
    return jsonify({"success": True})


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route("/liked")
def liked():
    return render_template("liked.html")


@app.route("/profile")
def profile():
    return render_template("profile.html", profile=user_profile, characters=characters, stories=stories)


@app.route("/update_profile", methods=["POST"])
def update_profile():
    global user_profile
    
    nicename = request.form.get("nicename", user_profile["nicename"])
    bio = request.form.get("bio", user_profile["bio"])
    
    user_profile["nicename"] = nicename
    user_profile["bio"] = bio
    
    # Handle profile image upload
    if "profile_image" in request.files:
        image_file = request.files.get("profile_image")
        filename = save_image(image_file)
        if filename:
            user_profile["profile_image"] = filename
    
    return redirect(url_for("profile"))


if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)