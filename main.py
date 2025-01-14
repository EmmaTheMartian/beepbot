from flask import Flask, request
import dotenv
import git
import hmac
import hashlib
import os
import requests
import requests.cookies
import datetime
import atexit


# .env variables
dotenv.load_dotenv()
BOT_USERNAME = os.environ['BOT_USERNAME']
BOT_PASSWORD = os.environ['BOT_PASSWORD']
RELOAD_REPO_SECRET = os.environ['RELOAD_REPO_SECRET']
BEEP_WEBHOOK_SECRET = os.environ['BEEP_WEBHOOK_SECRET']
BEEP_URL = os.environ['BEEP_URL']

# globals
app = Flask(__name__)
repo = git.Repo('./')
session = requests.Session()
whoami = None


# utility functions
def is_valid_signature(x_hub_signature, data, private_key) -> bool:
	# x_hub_signature and data are from the webhook payload
	# private key is your webhook secret
	hash_algorithm, github_signature = x_hub_signature.split('=', 1)
	algorithm = hashlib.__dict__.get(hash_algorithm)
	encoded_key = bytes(private_key, 'latin-1')
	mac = hmac.new(encoded_key, msg = data, digestmod = algorithm)
	return hmac.compare_digest(mac.hexdigest(), github_signature)


# routes
@app.route('/webhook', methods = ['POST'])
def webhook():
	x_hub_signature = request.headers.get('X-Hub-Signature')
	if not is_valid_signature(x_hub_signature, request.data, BEEP_WEBHOOK_SECRET):
		return 'invalid signature', 418

	if request.method != 'POST':
		return 'wrong event type', 400

	if session.cookies.get('token', default = '') == '':
		return 'bot not logged in'

	data = request.get_json()
	commits = data['commits']
	body = f"{data['before']} -> {data['after']}\n---\n"
	body += '\n'.join([f"- {it['message']} ({it['url']})" for it in commits])
	session.post(BEEP_URL + '/api/post/new_post', timeout = 10, data = {
		'title': f"pushed {len(commits)} commit{'s' if len(commits) > 1 else ''}",
		'body': body
	})

	return 'updated successfully'


@app.route('/update', methods = ['POST'])
def update():
	x_hub_signature = request.headers.get('X-Hub-Signature')
	if not is_valid_signature(x_hub_signature, request.data, RELOAD_REPO_SECRET):
		return 'invalid signature', 418

	if request.method != 'POST':
		return 'wrong event type', 400

	print('-> updating bot...')
	repo.remotes.origin.pull()
	return 'updated successfully'


@app.route('/')
def index():
	return f'bot running :sunglasses: (commit: {repo.commit().hexsha})\nlogged in as: {whoami}'


# main code
def _atexit():
	print('-> logging out...')
	requests.post(BEEP_URL + '/api/user/full_logout')
atexit.register(_atexit)

start = datetime.datetime.now()

# log into beep
print('-> logging in...')
response = session.post(BEEP_URL + '/api/user/login', data = {
	'username': BOT_USERNAME,
	'password': BOT_PASSWORD
})

# log who we are (useful for debugging)
whoami = session.get(BEEP_URL + '/api/user/whoami').text
print('-> logged in as: ' + whoami)

# make a "bot online" post
stop = datetime.datetime.now() - start
session.post(BEEP_URL + '/api/post/new_post', data = {
	'title': 'bot online',
	'body': f'took {stop.seconds}s to start.'
})

# run app
# uncomment if you are not using wsgi
# app.run()
