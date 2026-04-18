# ===== Standard Library =====
import os
import random
import sqlite3

# ===== Third-party Libraries =====
from flask import (
    Flask,
    redirect,
    url_for,
    session,
    request,
    render_template,
)

from authlib.integrations.flask_client import OAuth
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

# ===== Local Modules =====
from database import get_db, init_db

# Flask App
app = Flask(__name__)
app.secret_key = "0842476460"

# Image
UPLOAD_FOLDER = "static/img/users_profile"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

# OAuth Google Login
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='501075894042-he7a37mt0osbt116ef2sjds0k3pcpf4k.apps.googleusercontent.com',
    client_secret='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',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)


def calculate_tdee(gender, age, weight, height, activity, bodyfat):

    age = int(age)
    weight = float(weight)
    height = float(height)
    bodyfat = float(bodyfat)

    lbm = weight * (1 - bodyfat / 100)
    bmr = (10 * lbm) + (6.25 * height) - (5 * age) + (5 if gender == "male" else -161)

    activity_rate = {
        "athlete": 1.9,
        "heavy": 1.725,
        "moderate": 1.55,
        "light": 1.375
    }.get(activity, 1.2)

    tdee = bmr * activity_rate

    return (bmr, tdee)

# 
def check_login():
    if "user_id" not in session:
        return redirect("/")

    db = get_db()
    c = db.cursor()
    c.execute(
        "SELECT 1 FROM user_calculations WHERE user_id=?",
        (session["user_id"],)
    )
    if not c.fetchone():
        session.clear()
        return redirect("/")
    

    
from flask import request
import requests
@app.route("/callback")
def callback():
    code = request.args.get("code")

    token_response = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": os.getenv("CLIENT_ID"),
            "client_secret": os.getenv("CLIENT_ID"),
            "code": code
        }
    )

    token_json = token_response.json()
    access_token = token_json.get("access_token")

    return f"Access token: {access_token}"

# -------------------- Index --------------------
@app.route('/')
def index():
    user = session.get('profile')

    if user:
        return f"""
        <h2>Welcome {user['name']}</h2>
        <p>{user['email']}</p>
        <a href="/logout">Logout</a>
    """
    return render_template('index.html')

# -------------------- Login --------------------
@app.route('/login', methods=['GET'])
def login():
    return render_template("login.html")


# -------------------- Home --------------------
@app.route('/home', methods=['GET'])
def home():
    return render_template("home.html")


@app.route('/calculator', methods=['GET'])
def calculator():
    return render_template("tdee_calculator.html")


@app.route('/google_login')
def google_login():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)


# -------------------- Google Callback --------------------
    # -------------------- อยู่ใน Google API
@app.route('/login/callback')
def authorize():
    token = google.authorize_access_token()

    user_info = google.get(
        'https://openidconnect.googleapis.com/v1/userinfo'
    ).json()

    google_id = user_info['sub']
    email = user_info['email']
    name = user_info['name']
    picture = user_info.get('picture').replace("s96", "s300")

    db = get_db()
    c = db.cursor()

    c.execute(
        "SELECT id, google_id, email, name FROM google_users WHERE google_id=?",
        (google_id,)
    )
    user = c.fetchone()

    # ---------- ยังไม่เคยสมัคร ----------
    if user is None:
        session.clear()
        session['temp_google'] = {
            'google_id': google_id,
            'email': email,
            'name': name,
            'picture': picture
        }
        db.close()
        return redirect('/profile-setup')
    # ---------- เคยสมัครแล้ว ----------
    else:
        session.clear()
        session['user_id'] = user[0]
        session['name'] = user[3]
        session['email'] = user[2]
        session['user_type'] = 'google'

    db.close()
    return redirect('/dashboard')

@app.route('/profile-setup', methods=['GET'])
def profile_setup():
    if "temp_google" not in session:
        return redirect("/")
    else:
        return render_template("profile_setup.html")
  

#  -------------------- Profile Setup --------------------

@app.route('/profilesub', methods=['POST'])
def profilesub():
    if "temp_google" not in session:
        return redirect("/")

    user = session["temp_google"]

    gender = request.form["gender"]
    age = int(request.form["age"])
    weight = float(request.form["weight"])
    height = float(request.form["height"])
    activity = request.form["activity"]
    bodyfat = float(request.form["bodyfat"])

    lbm = weight * (1 - bodyfat/100)
    bmr = (10 * lbm) + (6.25 * height) - (5 * age) + (5 if gender == "male" else -161)


    activity_rate = {
        "light": 1.375,
        "moderate": 1.55,
        "heavy": 1.725,
        "athlete": 1.9
    }.get(activity, 1.2)

    tdee = bmr * activity_rate
    cutting = tdee - 500
    bulking = tdee + 500


    def highcarb(total_cal, weight, fat_multi):
        protein = weight * 2
        fat = weight * fat_multi
        carb = (total_cal - (protein * 4 + fat * 9)) / 4
        return round(carb), round(protein), round(fat)

    def highfat(total_cal, weight, fat_multi):
        protein = weight * 2.5
        fat = weight * fat_multi
        carb = (total_cal - (protein * 4 + fat * 9)) / 4
        return round(carb), round(protein), round(fat)

    # -------------------- High carb
    main_carb, main_protein, main_fat = highcarb(tdee, weight, 1)
    cut_carb, cut_protein, cut_fat = highcarb(cutting, weight, 0.75)
    bulk_carb, bulk_protein, bulk_fat = highcarb(bulking, weight, 1.5)

    # -------------------- High fat
    hfmain_carb, hfmain_protein, hfmain_fat = highfat(tdee, weight, 2)
    hfcut_carb, hfcut_protein, hfcut_fat = highfat(cutting, weight, 1.5)
    hfbulk_carb, hfbulk_protein, hfbulk_fat = highfat(bulking, weight, 2.5)

    db = get_db()
    c = db.cursor()


    c.execute("""
        INSERT INTO google_users (google_id, email, name, picture, gender, age, weight, height, activity, bodyfat)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
        (user["google_id"], user["email"], user["name"], user.get("picture"), 
        gender, age, weight, height, activity, bodyfat))
    
    user_id = c.lastrowid

    c.execute("""
    INSERT INTO user_calculations (user_id, user_type, tdee, bmr)
        VALUES (?, ?, ?, ?)
    """, (user_id, "google", tdee, bmr))


    

    db.commit()
    db.close()
    
    session.clear()
    session["user_id"] = user_id
    session["user_type"] = "google"
    session["name"] = user["name"]
    session["email"] = user["email"]

    
    return render_template(
    "data_profile.html",
    age=age, weight=weight, height=height, bodyfat=bodyfat, gender=gender,
    lbm=round(lbm,1), 
    bmr=round(bmr), 
    tdee=round(tdee),
    cutting=round(cutting), 
    bulking=round(bulking),


    # -------------------- High Carb Macros
    main_carb=main_carb, main_protein=main_protein, main_fat=main_fat,
    bulk_carb=bulk_carb, bulk_protein=bulk_protein, bulk_fat=bulk_fat,
    cut_carb=cut_carb, cut_protein=cut_protein, cut_fat=cut_fat,

    # -------------------- High Fat Macros
    hfmain_carb=hfmain_carb, hfmain_protein=hfmain_protein, hfmain_fat=hfmain_fat,
    hfbulk_carb=hfbulk_carb, hfbulk_protein=hfbulk_protein, hfbulk_fat=hfbulk_fat,
    hfcut_carb=hfcut_carb, hfcut_protein=hfcut_protein, hfcut_fat=hfcut_fat
)

# -------------------- Admin --------------------
@app.route("/admin")
def admin():

    if not session.get("is_admin"):
        return redirect("/login")

    db = get_db()
    db.row_factory = sqlite3.Row
    c = db.cursor()

    # -------------------- ดึงอาหารทั้งหมด
    c.execute("SELECT * FROM base_food")
    foods = c.fetchall()

    # -------------------- ดึงผู้ใช้ guest
    c.execute("SELECT * FROM guest_users")
    guest_users = c.fetchall()

    # -------------------- ดึงผู้ใช้ google
    c.execute("SELECT * FROM google_users")
    google_users = c.fetchall()

    db.close()

    return render_template(
        "admin.html",
        foods=foods,
        guest_users=guest_users,
        google_users=google_users
    )



@app.route("/add_base_food", methods=["GET", "POST"])
def add_base_food():
    if request.method == "POST":
        db = get_db()
        c = db.cursor()

        c.execute("""
            INSERT INTO base_food
            (food_name, category, base_cal, base_carb, base_protein, base_fat)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            request.form["food_name"],
            request.form["category"],
            request.form["base_cal"],
            request.form["base_carb"],
            request.form["base_protein"],
            request.form["base_fat"]
        ))

        db.commit()
        db.close()
        return redirect("/admin")
    else:
        return render_template("base_food.html")



@app.route("/edit_users/<user_type>/<int:user_id>", methods=["GET", "POST"])
def edit_users(user_type, user_id):

    if not session.get("is_admin"):
        return redirect("/login")

    db = get_db()
    db.row_factory = sqlite3.Row
    c = db.cursor()

    table = "guest_users" if user_type == "guest" else "google_users"

    if request.method == "POST":

        if user_type == "guest":
            c.execute("""
                UPDATE guest_users SET username=?, gender=?, age=?, weight=?, height=?, activity=?, bodyfat=? WHERE id=?
            """, (
                request.form["username"],
                request.form["gender"],
                request.form["age"],
                request.form["weight"],
                request.form["height"],
                request.form["activity"],
                request.form["bodyfat"],
                user_id
            ))

        elif user_type == "google":
            c.execute("""
                UPDATE google_users SET email=? WHERE id=?
            """, (
                request.form["email"],
                user_id
            ))

        db.commit()
        db.close()
        return redirect("/admin")

    c.execute(f"SELECT * FROM {table} WHERE id=?", (user_id,))
    user = c.fetchone()

    db.close()

    return render_template("edit_users.html", user=user, user_type=user_type)



# -----------------------------
# Logout
# -----------------------------


@app.route('/logout')
def logout():

    session.clear()
    return redirect('/')

# -----------------------------
# คำนวณ TDEE
# -----------------------------



#-------------------------------------------------------------------------------------
@app.route('/guest_register', methods=['GET'])
def guest_register():
    return render_template("guest_register.html")

@app.route('/guest_login', methods=['GET'])
def guest_login():
    return render_template("guest_login.html")



@app.route('/guest_resubmit', methods=['GET', 'POST'])
def guest_resubmit():

    if request.method == "GET":
        return redirect(url_for("guest_register"))

    username = request.form["username"]
    password = request.form["password"]


    age = int(request.form["age"])
    weight = float(request.form["weight"])
    height = float(request.form["height"])
    bodyfat = float(request.form["bodyfat"])
    gender = request.form["gender"]
    activity = request.form["activity"]

    lbm = weight * (1 - bodyfat/100)
    bmr = (10 * lbm) + (6.25 * height) - (5 * age) + (5 if gender == "male" else -161)

    activity_rate = {
        "athlete": 1.9,
        "heavy": 1.725,
        "moderate": 1.55,
        "light": 1.375
    }.get(activity, 1.2)

    tdee = bmr * activity_rate
    cutting = tdee - 500
    bulking = tdee + 500


    def highcarb(total_cal, weight, fat_multi):
        protein = weight * 2
        fat = weight * fat_multi
        carb = (total_cal - (protein * 4 + fat * 9)) / 4
        return round(carb), round(protein), round(fat)

    def highfat(total_cal, weight, fat_multi):
        protein = weight * 2.5
        fat = weight * fat_multi
        carb = (total_cal - (protein * 4 + fat * 9)) / 4
        return round(carb), round(protein), round(fat)

    
    main_carb, main_protein, main_fat = highcarb(tdee, weight, 1)
    cut_carb, cut_protein, cut_fat = highcarb(cutting, weight, 0.75)
    bulk_carb, bulk_protein, bulk_fat = highcarb(bulking, weight, 1.5)

    hfmain_carb, hfmain_protein, hfmain_fat = highfat(tdee, weight, 2)
    hfcut_carb, hfcut_protein, hfcut_fat = highfat(cutting, weight, 1.5)
    hfbulk_carb, hfbulk_protein, hfbulk_fat = highfat(bulking, weight, 2.5)

    password_hash = generate_password_hash(password)

    db = get_db()
    c = db.cursor()

    c.execute(
        "SELECT 1 FROM guest_users WHERE username = ?",
        (username,)
    )
    if c.fetchone():
        db.close()
        return render_template("guest_register.html", error="ชื่อผู้ใช้ถูกใช้ไปแล้ว")
    
    c.execute("""
        INSERT INTO guest_users (username, password_hash, gender, age, weight, height, activity, bodyfat)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (username, password_hash, gender, age, weight, height, activity, bodyfat))

    user_id = c.lastrowid

    c.execute("""
    INSERT INTO user_calculations (user_id, user_type, bmr, tdee)
    VALUES (?, ?, ?, ?)
    """, (user_id, "guest", bmr, tdee))


    session.clear()
    session["user_id"] = user_id
    session["user_type"] = "guest"
    session["username"] = username

    db.commit()
    db.close()

    return render_template("data_profile.html",
        age=age, weight=weight, height=height, bodyfat=bodyfat, gender=gender,
        lbm=round(lbm,1),
        bmr=round(bmr),
        tdee=round(tdee),
        cutting=round(cutting),
        bulking=round(bulking),

        # High Carb
        main_carb=main_carb, main_protein=main_protein, main_fat=main_fat,
        bulk_carb=bulk_carb, bulk_protein=bulk_protein, bulk_fat=bulk_fat,
        cut_carb=cut_carb, cut_protein=cut_protein, cut_fat=cut_fat,

        # High Fat
        hfmain_carb=hfmain_carb, hfmain_protein=hfmain_protein, hfmain_fat=hfmain_fat,
        hfbulk_carb=hfbulk_carb, hfbulk_protein=hfbulk_protein, hfbulk_fat=hfbulk_fat,
        hfcut_carb=hfcut_carb, hfcut_protein=hfcut_protein, hfcut_fat=hfcut_fat
    )



@app.route('/guest_logsubmit', methods=['POST'])
def guest_logsubmit():

    username = request.form["username"]
    password = request.form["password"]

    # ---------- ADMIN LOGIN ----------
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD_HASH = "scrypt:32768:8:1$ETMibwMfIvWGUV2Z$f87e7ca3f453aa9812c81e55635c89410df156430bf01a269e93ee9c121a54f3600a54a1a16b65a7fc34c8fbf8f67fc9196c3826e1ddb4c36df8d6e42b6f1e71"

    if username == ADMIN_USERNAME:
        if check_password_hash(ADMIN_PASSWORD_HASH, password):
            session.clear()
            session["is_admin"] = True
            session["username"] = "admin"
            return redirect("/admin")
        else:
            return "รหัสผ่าน admin ไม่ถูกต้อง"
    # ---------------------------------

    db = get_db()
    db.row_factory = sqlite3.Row
    c = db.cursor()

    c.execute("SELECT * FROM guest_users WHERE username=?", (username,))
    user = c.fetchone()

    if user and check_password_hash(user["password_hash"], password):
        session.clear()
        session.permanent = True
        session["user_id"] = user["id"]
        session["user_type"] = "guest"
        session["username"] = user["username"]

        db.close()
        return redirect("/dashboard")
    else:
        db.close()

    return "ชื่อผู้ใช้หรือรหัสผ่านผิด"




@app.route('/dashboard')
def dashboard():
    check = check_login()
    if check:
        return check

    db = get_db()
    c = db.cursor()

    user_id = session["user_id"]
    user_type = session["user_type"]

    # ---------- user ----------
    if user_type == "google":
        c.execute(
            "SELECT name, picture FROM google_users WHERE id=?",
            (user_id,)
        )
    else:
        c.execute(
            "SELECT username AS name, picture FROM guest_users WHERE id=?",
            (user_id,)
        )

    user = c.fetchone()
    if not user:
        session.clear()
        db.close()
        return redirect("/")

    # ---------- TDEE ----------

    c.execute("""
    SELECT food_name, base_cal, base_carb, base_protein, base_fat FROM base_food ORDER BY food_name ASC
    """)
    base_foods = c.fetchall()
    
    c.execute("""
        SELECT tdee FROM user_calculations WHERE user_id=? AND user_type=? ORDER BY created_at DESC
        LIMIT 1
    """, (user_id, user_type))
    cal = c.fetchone()
    tdee = round(cal["tdee"]) if cal else 0

    # ---------- foods today ----------
    c.execute("""
        SELECT food_name, calories FROM food_logs WHERE user_id=? AND user_type=? AND log_date=CURRENT_DATE
    """, (user_id, user_type))
    foods = c.fetchall()

    # ---------- eaten ----------
    c.execute("""
        SELECT COALESCE(SUM(calories), 0) AS total FROM food_logs WHERE user_id=? AND user_type=? AND log_date=CURRENT_DATE
    """, (user_id, user_type))
    eaten = c.fetchone()["total"]

    remaining = tdee - eaten

    db.close()

    return render_template(
        "dashboard.html",
        user=user,
        tdee=tdee,
        foods=foods,
        eaten=eaten,
        remaining=remaining,
        base_foods = base_foods,
    )


# --------------- บันทึกสารอาหาร ---------------
@app.route("/food_log", methods=["GET", "POST"])
def food_log():
    user_id = session.get("user_id")
    user_type = session.get("user_type")

    if not user_id:
        return redirect("/login")

    db = get_db()
    db.row_factory = sqlite3.Row
    c = db.cursor()

    if request.method == "POST":
        food = request.form.get("food")
        protein = float(request.form.get("protein") or 0)
        carb = float(request.form.get("carb") or 0)
        fat = float(request.form.get("fat") or 0)

        cal = (protein * 4) + (carb * 4) + (fat * 9)

        c.execute("""
            INSERT INTO food_logs
            (user_id, user_type, food_name, calories, carb, protein, fat) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, user_type, food, cal, carb, protein, fat))

        db.commit()
        return redirect('/food_log')

    c.execute("""
        SELECT * FROM food_logs 
        WHERE user_id=? AND user_type=? 
        AND date(created_at)=date('now') 
        ORDER BY id DESC
    """, (user_id, user_type))
    foods = c.fetchall()

    c.execute("""
        SELECT
            SUM(calories) as total_cal,
            SUM(carb) as total_carb,
            SUM(protein) as total_protein,
            SUM(fat) as total_fat
        FROM food_logs
        WHERE user_id=? AND user_type=?
        AND date(created_at)=date('now')
    """, (user_id, user_type))
    total = c.fetchone()

    db.close()
    return render_template("food_log.html", foods=foods, total=total)





@app.route("/edit_food/<int:food_id>", methods=["GET", "POST"])
def edit_food(food_id):

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    db = get_db()
    db.row_factory = sqlite3.Row
    c = db.cursor()

    c.execute("""
        SELECT * FROM food_logs 
        WHERE id=? AND user_id=?
    """, (food_id, user_id))

    food = c.fetchone()

    if not food:
        db.close()
        return "ไม่พบรายการอาหาร"
    
    if request.method == "POST":
        food_name = request.form.get("food_name")
        carb = float(request.form.get("carb") or 0)
        protein = float(request.form.get("protein") or 0)
        fat = float(request.form.get("fat") or 0)

        manual_cal = request.form.get("calories")
        manual_cal = float(manual_cal) if manual_cal else 0

        old_carb = float(food["carb"] or 0)
        old_protein = float(food["protein"] or 0)
        old_fat = float(food["fat"] or 0)

        # ถ้าแก้สารอาหาร → คำนวณใหม่ทันที
        if (carb != old_carb) or (protein != old_protein) or (fat != old_fat):
            cal = (carb * 4) + (protein * 4) + (fat * 9)
        else:
            # ถ้าไม่ได้แก้สารอาหาร → ใช้แคลที่กรอกเอง
            cal = manual_cal

        c.execute("""
            UPDATE food_logs 
            SET food_name=?, calories=?, carb=?, protein=?, fat=? 
            WHERE id=? AND user_id=?
        """, (food_name, cal, carb, protein, fat, food_id, user_id))

        db.commit()
        db.close()
        return redirect("/food_log")

    db.close()
    return render_template("edit_food.html", food=food)



@app.route("/food_log/delete/<int:food_id>")
def delete_food(food_id):

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    db = get_db()
    c = db.cursor()

    c.execute("""
        DELETE FROM food_logs WHERE id=? AND user_id=?
    """, (food_id, user_id))

    db.commit()
    db.close()

    return redirect("/food_log")



@app.route("/profile")
def profile():
    check = check_login()
    if check:
        return
    user_id = session.get("user_id")
    user_type = session.get("user_type")

    if not user_id or not user_type:
        return redirect("/")

    connect = sqlite3.connect("EatForFit.db")
    connect.row_factory = sqlite3.Row
    c = connect.cursor()

    user = None

    # ถ้าเป็น guest ให้เรียกตาราง guest_users
    if user_type == "guest":
        c.execute("SELECT * FROM guest_users WHERE id=?", (user_id,))
        user = c.fetchone()

    # ถ้าเป็น google ให้เรียกตาราง google_users
    elif user_type == "google":
        c.execute("SELECT * FROM google_users WHERE id=?", (user_id,))
        user = c.fetchone()

    connect.close()

    # ไม่มีกลับหน้าแรก
    if user is None:
        return redirect("/")

    return render_template("data_profile.html", user=user)




@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    user_type = session.get("user_type")

    # ถ้าเป็น guest ให้ table เท่ากับ guest_users
    if user_type == "guest":
        table = "guest_users"

    # ถ้าเป็น google ให้ table เท่ากับ google_users
    elif user_type == "google":
        table = "google_users"
    else:
        return redirect("/login")

    db = get_db()
    db.row_factory = sqlite3.Row
    c = db.cursor()

    # --------------- รับ Request จาก Form ---------------
    if request.method == "POST":
        gender = request.form.get("gender")
        age = request.form.get("age")
        weight = request.form.get("weight")
        height = request.form.get("height")
        activity = request.form.get("activity")
        bodyfat = request.form.get("bodyfat")

        # --------------- อัปเดตโปรไฟล์ ---------------
        c.execute(f"""
            UPDATE {table} SET gender=?, age=?, weight=?, height=?, activity=?, bodyfat=? WHERE id=?
        """, (gender, age, weight, height, activity, bodyfat, user_id))

        bmr, tdee = calculate_tdee(gender, age, weight, height, activity, bodyfat)

        c.execute("""
            UPDATE user_calculations SET bmr=?, tdee=? WHERE user_id=?
        """, (bmr, tdee, user_id))

        db.commit()
        db.close()

        return redirect("/profile")

    # โหลดข้อมูลมาแสดง
    c.execute(f"SELECT * FROM {table} WHERE id=?", (user_id,))
    user = c.fetchone()

    db.close()

    return render_template("edit_profile.html", user=user)



@app.route("/workout")
def workout():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM workouts")
    workouts = c.fetchall()
    return render_template("workout.html", workouts=workouts)
    


@app.route('/get_today_summary')
def get_today_summary():
    user_id = session.get("user_id")

    connect = sqlite3.connect("EatForFit.db")
    c = connect.cursor()

    c.execute("""
        SELECT 
            IFNULL(SUM(carb),0),
            IFNULL(SUM(protein),0),
            IFNULL(SUM(fat),0),
            IFNULL(SUM(calories),0)
        FROM food_logs
        WHERE user_id = ?
        AND DATE(created_at) = DATE('now','localtime')
    """, (user_id,))

    carb, protein, fat, calories = c.fetchone()
    connect.close()

    return {
        "carb": carb,
        "protein": protein,
        "fat": fat,
        "calories": calories
    }


@app.route('/calculate', methods=['POST'])
def calculate():
    gender = request.form['gender']
    age = int(request.form['age'])
    weight = float(request.form['weight'])
    height = float(request.form['height'])
    activity = request.form['activity']
    bodyfat = int(request.form['bodyfat'])

    lbm = weight * (1 - bodyfat/100)
    bmr = (10 * lbm) + (6.25 * height) - (5 * age) + (5 if gender == "male" else -161)

    # -------------------- Activity Rate --------------------
    activity_rate = {
        "athlete": 1.9,
        "heavy": 1.725,
        "moderate": 1.55,
        "light": 1.375,
        "sedentary": 1.2
    }.get(activity, 1.2)

    tdee = bmr * activity_rate
    cutting = tdee - 500
    bulking = tdee + 500


    # -------- โปรตีนตามระดับการออกกำลังกาย --------
    def protein_multi(activity_level):
        if activity_level == "athlete":
            return 2.2
        elif activity_level == "heavy":
            return 2
        elif activity_level == "moderate":
            return 1.75
        elif activity_level == "light":
            return 1.5
        else:
            return 1.25


    # -------- สูตรกลางใช้กับทุกแบบ --------
    def calculate_macros(total_cal, weight, fat_multi, activity_level):

        # โปรตีนตาม activity
        protein = weight * protein_multi(activity_level)

        # ไขมันตาม phase
        fat = weight * fat_multi

        # คาร์บที่เหลือ
        carb = (total_cal - (protein * 4 + fat * 9)) / 4

        # กันติดลบ (ใช้ได้กับ High Fat ด้วย)
        if carb < 0:
            carb = 0
            fat = (total_cal - (protein * 4)) / 9
            if fat < 0:
                fat = 0

        return round(carb), round(protein), round(fat)

    # -------- Maintenance --------
    main_carb, main_protein, main_fat = calculate_macros(
        tdee, weight, 1, activity
    )

    # -------- Cutting --------
    cut_carb, cut_protein, cut_fat = calculate_macros(
        cutting, weight, 0.75, activity
    )

    # -------- Bulking --------
    bulk_carb, bulk_protein, bulk_fat = calculate_macros(
        bulking, weight, 1.5, activity
    )



    hfmain_carb, hfmain_protein, hfmain_fat = calculate_macros(
        tdee, weight, 1.75, activity
    )

    hfcut_carb, hfcut_protein, hfcut_fat = calculate_macros(
        cutting, weight, 1.5, activity
    )

    hfbulk_carb, hfbulk_protein, hfbulk_fat = calculate_macros(
        bulking, weight, 2, activity
    )
    
    connect = sqlite3.connect("EatForFit.db")
    c = connect.cursor()
    c.execute("""INSERT INTO data_test(age, weight, height, gender, activity, bodyfat, bmr, tdee) 
              VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", 
            (age, weight, height, gender, activity, bodyfat, bmr, tdee,))
    
    connect.commit()    
    connect.close()
    
    # -------------------- ส่งค่าไปยังเว็บ --------------------
    return render_template(
        "tdee_result.html",
        gender=gender, age=age, weight=weight, height=height, activity=activity, bodyfat=bodyfat, 
        lbm=round(lbm,1), 
        bmr=round(bmr), 
        tdee=round(tdee),
        cutting=round(cutting), 
        bulking=round(bulking),

        # -------------------- High Carb Macros --------------------
        main_carb=main_carb, main_protein=main_protein, main_fat=main_fat,
        bulk_carb=bulk_carb, bulk_protein=bulk_protein, bulk_fat=bulk_fat,
        cut_carb=cut_carb, cut_protein=cut_protein, cut_fat=cut_fat,

        # High Fat
        hfmain_carb=hfmain_carb, hfmain_protein=hfmain_protein, hfmain_fat=hfmain_fat,
        hfbulk_carb=hfbulk_carb, hfbulk_protein=hfbulk_protein, hfbulk_fat=hfbulk_fat,
        hfcut_carb=hfcut_carb, hfcut_protein=hfcut_protein, hfcut_fat=hfcut_fat
    )
        
        
if __name__ == '__main__':
    init_db()
    app.run(debug=True,host="0.0.0.0", use_reloader=True)
    
