from datetime import timedelta
from functools import update_wrapper
import json
import os
from flask import Flask, make_response, request, current_app
import requests
from requests.options import (
        BAD_REQUEST as HTTP_BAD_REQUEST,
        )
from tasks import update_project, update_projects as update_pjs_task

THE_KEY = os.environ['FLASK_KEY']

app = Flask(__name__)

def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

@app.route('/add-project/', methods=['POST'])
@crossdomain(origin="*")
def submit_project():
    project_url = request.form.get('project_url')
    project_details = update_project(project_url)
    if project_details:
        resp = make_response(json.dumps(project_details))
        resp.headers['Content-Type'] = 'application/json'
        return resp
    else:
        return make_response('The URL you submitted, %s, does not appear to be a valid Github repo' % project_url, HTTP_BAD_REQUEST)

@app.route('/delete-project/', methods=['POST'])
def delete_project():
    if request.form.get('the_key') == THE_KEY:
        project_url = request.form.get('project_url')
        with open('data/projects.json', 'rb') as f:
            projects = json.loads(f.read())
        try:
            projects.remove(project_url)
            with open('data/projects.json', 'wb') as f:
                f.write(json.dumps(projects))
            resp = make_response('Deleted %s' % project_url)
        except ValueError:
            resp = make_response('%s is not in the registry', HTTP_BAD_REQUEST)
    else:
        resp = make_response("I can't do that Dave", HTTP_BAD_REQUEST)
    return resp

@app.route('/update-projects/', methods=['GET'])
def update_projects():
    update_pjs_task.delay()
    resp = make_response('Executed update task')
    return resp

if __name__ == "__main__":
    app.run(debug=True, port=6666)
