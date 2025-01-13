import flask
import dotenv

app = flask.Flask(__name__)

@app.route('/webhook', methods = ['POST'])
def webhook():
	print(flask.request.json)
	return flask.Response(status = 200)

if __name__ == '__main__':
	app.run()
