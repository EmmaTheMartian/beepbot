import flask
import dotenv
import git
import hmac
import hashlib
import os

dotenv.load_dotenv()

BOT_USERNAME = os.environ['BOT_USERNAME']
BOT_PASSWORD = os.environ['BOT_PASSWORD']
RELOAD_REPO_SECRET = os.environ['RELOAD_REPO_SECRET']
BEEP_WEBHOOK_SECRET = os.environ['BEEP_WEBHOOK_SECRET']

app = flask.Flask(__name__)

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
	print(flask.request.json)
	return flask.Response(status = 200)

@app.route('/update', methods = ['POST'])
def update():
	x_hub_signature = flask.request.headers.get('X-Hub-Signature')
	if not is_valid_signature(x_hub_signature, flask.request.data, update_webhook_secret):
		return 'invalid signature', 418

	if flask.request.method == 'POST':
		print('-> updating bot...')
		repo = git.Repo('/home/beeper/beepbot/')
		origin = repo.remotes.origin
		origin.pull()
		return 'updated successfully'
	else:
		return 'wrong event type', 400

@app.route('/')
def index():
	return 'webapp running :sunglasses:'

if __name__ == '__main__':
	app.run()
