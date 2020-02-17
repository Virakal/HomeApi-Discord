#!/usr/bin/env python

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlencode, urlparse

import discord
import requests
import webbrowser
from sanction import Client, transport_headers

DISCORD_CLIENT_ID = '678765395821199380'
DISCORD_CLIENT_SCOPES = [
	'identify',
	'messages.read',
]

# This is disgusting
class GotResponseException(BaseException):
	def __init__(self, response, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.response = response


class OauthHandler(BaseHTTPRequestHandler):
	with open('./homeapi_discord/secret.txt', 'r') as f:
		client_secret = f.readline().strip()

	def do_GET(self):
		url = urlparse(self.path)

		if url.path == '/login':
			args = dict(parse_qsl(url.query))
			assert 'code' in args
			response = self.request_auth(args['code'])
			self.wfile.write(b'Done, you can close this tab.')
			self.wfile.close()
			raise GotResponseException(response)
		else:
			self.wfile.write(b"Invalid URL!")

	def request_auth(self, code):
		token_url = 'https://discordapp.com/api/oauth2/token'
		headers = {
			'Content-Type': 'application/x-www-form-urlencoded'
		}

		r = requests.post(token_url, headers=headers, data={
			"client_id": DISCORD_CLIENT_ID,
			"client_secret": self.client_secret,
			"code": code,
			"grant_type": "authorization_code",
			"redirect_url": 'http://localhost:8069/login',
			"scope": ' '.join(DISCORD_CLIENT_SCOPES),
		})

		json = r.json()

		if 'error' not in json:
			return json

		raise Exception('Error in authorisation: ' + repr(json))


class DiscordMessageHandler():
	token = None

	def get_token(self):
		scope = ' '.join(DISCORD_CLIENT_SCOPES)
		client_id = DISCORD_CLIENT_ID
		oauth_base_url = 'https://discordapp.com/api/oauth2/authorize'
		args = {
			"response_type": "code",
			"client_id": client_id,
			# "state": "todo",
			"scope": scope,
			"redirect_url": 'http://localhost:8069/login',
			"prompt": "none",
		}

		auth_url = f"{oauth_base_url}?{urlencode(args)}"
		webbrowser.open_new_tab(auth_url)

		print("Waiting for Oauth authorisation")

		server_address = ('', 8069)
		server = HTTPServer(server_address, OauthHandler)

		try:
			server.serve_forever()
		except GotResponseException as e:
			response = e.response

		self.oauth = response
		return response['access_token']

class DiscordClient(discord.Client):
	async def on_ready(self):
		print('Logged on as {0}!'.format(self.user))

if __name__ == '__main__':
	message_handler = DiscordMessageHandler()
	token = message_handler.get_token()
	client = DiscordClient()
	client.run(token)
