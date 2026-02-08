from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import os
import uuid
from PIL import Image
from flask_wtf import CSRFProtect

app = Flask(__name__)
app.secret_key = "change-this-secret-please-update-in-production"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Lütfen giriş yapınız.'

UPLOAD_FOLDER = "static/uploads/"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB limit
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}

# ============= VERİTABANI MODELLERİ =============

class User(UserMixin, db.Model):
    """Kullanıcı modeli"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nicename = db.Column(db.String(120), default="Kullanıcı")
    bio = db.Column(db.Text, default="Hoş geldiniz!")
    profile_image = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_active = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        """Şifreyi hashleyerek kaydet"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Şifre doğrulaması"""
        return check_password_hash(self.password_hash, password)


# ============= AYAR VE FONKSİYONLAR =============


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@login_manager.user_loader
def load_user(user_id):
    """Kullanıcı yükleyici"""
    return User.query.get(int(user_id))


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


# ============= AUTHENTICATION ROTLARI =============

@app.route("/register", methods=["GET", "POST"])
def register():
    """Kayıt sayfası"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        
        # Doğrulama
        if not username or not email or not password:
            flash("Lütfen tüm alanları doldurunuz.", "error")
            return redirect(url_for("register"))
        
        if len(username) < 3:
            flash("Kullanıcı adı en az 3 karakter olmalıdır.", "error")
            return redirect(url_for("register"))
        
        if len(password) < 6:
            flash("Şifre en az 6 karakter olmalıdır.", "error")
            return redirect(url_for("register"))
        
        if password != password_confirm:
            flash("Şifreler eşleşmiyor.", "error")
            return redirect(url_for("register"))
        
        # Kullanıcı kontrolü
        if User.query.filter_by(username=username).first():
            flash("Bu kullanıcı adı zaten kullanılıyor.", "error")
            return redirect(url_for("register"))
        
        if User.query.filter_by(email=email).first():
            flash("Bu email zaten kullanılıyor.", "error")
            return redirect(url_for("register"))
        
        # Yeni kullanıcı oluştur
        user = User(username=username, email=email)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash("Kayıt başarılı! Lütfen giriş yapınız.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            flash("Kayıt sırasında hata oluştu.", "error")
            return redirect(url_for("register"))
    
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Giriş sayfası"""
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            flash("Lütfen kullanıcı adı ve şifre girin.", "error")
            return redirect(url_for("login"))
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f"Hoş geldin {user.username}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("index"))
        else:
            flash("Hatalı kullanıcı adı veya şifre.", "error")
            return redirect(url_for("login"))
    
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """Çıkış"""
    logout_user()
    flash("Çıkış yaptınız.", "success")
    return redirect(url_for("index"))


# ============= GENEL ROTLAR =============
def index():
    return render_template("index.html")


@app.route("/api/characters")
def api_characters():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 8))
    start = (page-1)*per_page
    end = start + per_page
    # items = characters[start:end]
    return jsonify({
        "characters": [],
        "page": page,
        "has_more": False
    })


@app.route("/create")
@login_required
def create():
    return render_template("create.html")


@app.route("/add_character", methods=["GET", "POST"])
@login_required
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
            "image": filename,
            "user_id": current_user.id
        }
        # characters.append(character)
        return redirect(url_for("index"))
    return render_template("add.html", characters=[])


@app.route("/stories")
def stories_page():
    return render_template("stories.html", stories=[])


@app.route("/add_story", methods=["GET", "POST"])
@login_required
def add_story():
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        selected_chars = request.form.getlist("characters")
        story = {
            "id": uuid.uuid4().hex,
            "title": title,
            "content": content,
            "characters": selected_chars,
            "user_id": current_user.id
        }
        # stories.append(story)
        return redirect(url_for("stories_page"))
    return render_template("add_story.html", characters=[])


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


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", profile=current_user, characters=[], stories=[])


@app.route("/update_profile", methods=["POST"])
@login_required
def update_profile():
    nicename = request.form.get("nicename", current_user.nicename)
    bio = request.form.get("bio", current_user.bio)
    
    current_user.nicename = nicename
    current_user.bio = bio
    
    # Handle profile image upload
    if "profile_image" in request.files:
        image_file = request.files.get("profile_image")
        filename = save_image(image_file)
        if filename:
            current_user.profile_image = filename
    
    try:
        db.session.commit()
        flash("Profil başarıyla güncellendi.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Güncelleme sırasında hata oluştu.", "error")
    
    return redirect(url_for("profile"))


@app.route("/liked")
@login_required
def liked():
    return render_template("liked.html")


if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    with app.app_context():
        db.create_all()  # Veritabanı tablolarını oluştur
    
    app.run(debug=True)