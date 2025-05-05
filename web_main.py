import os

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask import send_file

from guitar_helper import GuitarHelper

app = Flask(__name__)
app.secret_key = "secret"  # 세션용 키

@app.route("/health")
def health_check():
    return jsonify(status="ok"), 200

@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":
        title = request.form["title"]
        url = request.form["url"]
        start_time = request.form.get("start_time") or None
        end_time = request.form.get("end_time") or None
        bpm = request.form.get("bpm", type=int) or 100
        output_root_dir = request.form.get("output_root_dir")

        if not output_root_dir or output_root_dir.strip() == "":
            output_root_dir = os.path.join(os.path.expanduser("~"), "Downloads")

        gh = GuitarHelper(title, url, output_root_dir)
        gh.set_bpm(bpm)
        gh.start_time = start_time
        gh.end_time = end_time
        gh.set_time_range(start_time, end_time)

        gh.download_youtube()
        gh.show_capture_guide_web(save_path="static/guide.jpg")  # 이미지 저장용 수정된 함수 필요

        # gh 객체는 세션으로 못 넘기니까 필요한 값만 저장
        session["params"] = {
            "title": title,
            "url": url,
            "start_time": start_time,
            "end_time": end_time,
            "bpm": bpm,
            "output_root_dir": output_root_dir,
        }

        return redirect(url_for("confirm_y"))

    return render_template("index.html")


@app.route("/confirm_y", methods=["GET", "POST"])
def confirm_y():
    if request.method == "POST":
        y_start = int(request.form["y_start"])
        y_end = int(request.form["y_end"])

        # 세션에서 파라미터 가져옴
        p = session.get("params")
        output_path = p['output_root_dir']
        gh = GuitarHelper(p["title"], p["url"], output_path)
        gh.set_bpm(p["bpm"])
        gh.start_time = p["start_time"]
        gh.end_time = p["end_time"]
        gh.set_time_range(p["start_time"], p["end_time"])

        # 이어서 처리
        gh.capture_video_frame(y_start, y_end)
        gh.remove_duplicate_imgs()
        pdf_path = gh.merge_jpgs_to_pdf()
        # gh.upload_pdf_to_google_dirve()

        params = session.get("params", {})
        params["pdf_path"] = pdf_path
        session["params"] = params  # 덮어쓰기!
        return redirect(url_for("download_pdf"))

    return render_template("confirm_y.html", guide_img="/static/guide.jpg")


@app.route("/start_confirm_y", methods=["POST"])
def start_confirm_y():
    session["y_start"] = request.form["y_start"]
    session["y_end"] = request.form["y_end"]
    return render_template("loading.html")  # 로딩 메시지 출력


@app.route("/process_confirm_y")
def process_confirm_y():
    y_start = int(session["y_start"])
    y_end = int(session["y_end"])
    p = session["params"]
    gh = GuitarHelper(p["title"], p["url"], p["output_root_dir"])
    gh.set_bpm(p["bpm"])
    gh.set_time_range(p["start_time"], p["end_time"])

    gh.capture_video_frame(y_start, y_end)
    gh.remove_duplicate_imgs()
    pdf_path = gh.merge_jpgs_to_pdf()

    params = session.get("params")
    params["pdf_path"] = pdf_path
    session["params"] = params

    return redirect(url_for("download_pdf"))


@app.route("/download_pdf")
def download_pdf():
    p = session.get("params")
    pdf_path = p.get("pdf_path")
    if pdf_path and os.path.exists(pdf_path):
        # 다운로드 후 홈으로 이동시키는 HTML 렌더링
        return render_template("success.html", pdf_path=pdf_path)
    else:
        return render_template("error.html", message="PDF 파일이 존재하지 않습니다.")


@app.route("/download_pdf_file")
def download_pdf_file():
    p = session.get("params")
    pdf_path = p.get("pdf_path")
    if pdf_path and os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True)
    else:
        return render_template("error.html", message="파일이 존재하지 않습니다.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
