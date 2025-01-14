from flask import Flask, request
import dotenv
import git
import hmac
import hashlib
import os
import requests
import requests.cookies
import datetime

dotenv.load_dotenv()

BOT_USERNAME = os.environ['BOT_USERNAME']
BOT_PASSWORD = os.environ['BOT_PASSWORD']
RELOAD_REPO_SECRET = os.environ['RELOAD_REPO_SECRET']
BEEP_WEBHOOK_SECRET = os.environ['BEEP_WEBHOOK_SECRET']
BEEP_URL = os.environ['BEEP_URL']

app = Flask(__name__)
repo = git.Repo('./')
session = requests.Session()


def is_valid_signature(x_hub_signature, data, private_key) -> bool:
	# x_hub_signature and data are from the webhook payload
	# private key is your webhook secret
	hash_algorithm, github_signature = x_hub_signature.split('=', 1)
	algorithm = hashlib.__dict__.get(hash_algorithm)
	encoded_key = bytes(private_key, 'latin-1')
	mac = hmac.new(encoded_key, msg = data, digestmod = algorithm)
	return hmac.compare_digest(mac.hexdigest(), github_signature)

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
	return 'bot running :sunglasses: (commit: ' + repo.commit().hexsha + ')'

if __name__ == '__main__':
	start = datetime.datetime.now()

	# log into beep
	print('-> logging in...')
	response = session.post(BEEP_URL + '/api/user/login', data = {
		'username': BOT_USERNAME,
		'password': BOT_PASSWORD
	})

	whoami = session.get(BEEP_URL + '/api/user/whoami')
	print('-> logged in as: ' + whoami.text)

	stop = datetime.datetime.now() - start

	# make a test post
	session.post(BEEP_URL + '/api/post/new_post', data = {
		'title': 'bot online',
		'body': f'took {stop.seconds}s to start.'
	})

	# run app
	app.run()

	print('-> logging out...')
	requests.post(BEEP_URL + '/api/user/full_logout')
