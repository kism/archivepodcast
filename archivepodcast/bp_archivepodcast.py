from flask import Flask, render_template, send_from_directory, redirect, Response


def generate_404():
    """We use the 404 template in a couple places"""
    returncode = 404
    render = render_template(
        "error.j2",
        errorcode=str(returncode),
        errortext="Page not found, how did you even?",
        settingsjson=settingsjson,
    )
    return render


@app.route("/")
def home():
    """Flask Home"""
    return render_template("home.j2", settingsjson=settingsjson, aboutpage=aboutpage)


@app.route("/index.html")
def home_indexhtml():
    """Flask Home, s3 backup compatible"""
    # This ensures that if you transparently redirect / to /index.html
    # for using in cloudflare r2 storage it will work
    # If the vm goes down you can change the main domain dns to point to r2
    # and everything should work.
    return render_template("home.j2", settingsjson=settingsjson, aboutpage=aboutpage)


@app.route("/about.html")
def home_abouthtml():
    """Flask Home, s3 backup compatible"""
    if aboutpage:
        return send_from_directory(settingsjson["webroot"], "about.html")
    returncode = 404
    return (
        generate_404(),
        returncode,
    )


@app.route("/content/<path:path>")
def send_content(path):
    """Serve Content"""
    response = None

    if settingsjson["storagebackend"] == "s3":
        newpath = settingsjson["cdndomain"] + "content/" + path.replace(settingsjson["webroot"], "")
        response = redirect(newpath, code=302)
        response.headers["Cache-Control"] = "public, max-age=10800"  # 10800 seconds = 3 hours
    else:
        response = send_from_directory(settingsjson["webroot"] + "/content", path)

    return response


@app.errorhandler(404)
# pylint: disable=unused-argument
def invalid_route(e):
    """404 Handler"""
    returncode = 404
    return (
        generate_404(),
        returncode,
    )


@app.route("/rss/<string:feed>", methods=["GET"])
def rss(feed):
    """Send RSS Feed"""
    logging.debug("Sending xml feed: %s", feed)
    xml = ""
    returncode = 200
    try:
        xml = PODCASTXML[feed]
    except TypeError:
        returncode = 500
        return (
            render_template(
                "error.j2",
                errorcode=str(returncode),
                errortext="The developer probably messed something up",
                settingsjson=settingsjson,
            ),
            returncode,
        )
    except KeyError:
        try:
            tree = Et.parse(settingsjson["webroot"] + "rss/" + feed)
            xml = Et.tostring(
                tree.getroot(),
                encoding="utf-8",
                method="xml",
                xml_declaration=True,
            )
            logging.warning('❗ Feed "%s" not live, sending cached version from disk', feed)

        except FileNotFoundError:
            returncode = 404
            return (
                render_template(
                    "error.j2",
                    errorcode=str(returncode),
                    errortext="Feed not found, you know you can copy and paste yeah?",
                    settingsjson=settingsjson,
                ),
                returncode,
            )
    return Response(xml, mimetype="application/rss+xml; charset=utf-8")


@app.route("/robots.txt")
def static_from_root():
    """Serve robots.txt"""
    response = Response(response="User-Agent: *\nDisallow: /\n", status=200, mimetype="text/plain")
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


@app.route("/favicon.ico")
def favicon():
    """Return the favicon"""
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )
