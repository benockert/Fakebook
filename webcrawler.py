# CS3700 Networks and Distributed Systems - Project 4
import argparse
import socket
import re
from urllib.parse import urlparse

# GLOBALS
VERSION = "HTTP/1.1"
GET = "GET"
POST = "POST"
ROOT = " /fakebook/ "
LOGIN = " /accounts/login/?next=/fakebook/ "

# Socket connection information
hostname = "fring.ccs.neu.edu"
port = 80

# POST and GET forms for the initial login sequence
post_header = POST + LOGIN + VERSION + "\nHost: %s\nCookie: " % hostname
get_header = GET + ROOT + VERSION + "\nHost: %s\nConnection: keep-alive\nCookie: " % hostname

# Secret flags
flags = []


class WebCrawler(object):
    def __init__(self, username, password, start_url):
        self.username = username
        self.password = password
        self.start = start_url
        self.csrf = ''
        self.sessionid = ''
        self.explored = set()
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # logs in to Fakebook
    def login(self):
        # GETS the html of the login page
        request = GET + LOGIN + VERSION + "\nHost:%s\n\n" % self.start
        self.client.send(request.encode())

        # gets the server's response (html of the webpage)
        response = self.client.recv(4096).decode("latin-1")

        # gets the CSRF token
        token_start = response.find('csrftoken=') + 10
        self.csrf = response[token_start:token_start + 32]

        # gets the session ID
        id_start = response.find('sessionid=') + 10
        self.sessionid = response[id_start:id_start + 32]

        # submits the login form with the two cookies
        form_entry = "username=" + self.username + "&password=" + self.password + "&csrfmiddlewaretoken=" \
                     + self.csrf + "&next=%2Ffakebook%2F"
        content_length = "\nContent-Length: " + str(len(form_entry)) + "\n\n"
        post = post_header + "csrftoken=" + self.csrf + "; sessionid=" + self.sessionid + content_length + form_entry

        self.client.send(post.encode())

        # gets the server's response to the post
        post_response = self.client.recv(4096).decode("latin-1")
        new_id_start = post_response.find('sessionid=') + 10
        self.sessionid = post_response[new_id_start:new_id_start + 32]

        self.get_root()

    # after logging in, get the root page's html (/fakebook/)
    def get_root(self):
        get_request = get_header + "csrftoken=" + self.csrf + "; sessionid=" + self.sessionid
        self.client.send(get_request.encode())

        # gets the server's response (html of the root webpage)
        # THIS IS WHERE I AM RECEIVING A 408 TIMEOUT
        root_response = self.client.recv(4096).decode("latin-1")

        # TODO get the root page links and begin crawling

    # TODO parse the html of each profile page, get the hrefs, add them to the queue
    def crawl(self, href):
        # GET request for the given profile page
        get = GET + " " + href + " " + VERSION + "\nHost: " + hostname + "\nCookie: csrftoken=" + self.csrf + \
              "; sessionid=" + self.sessionid
        self.client.send(get.encode())
        get_response = self.client.recv(4096).decode("latin-1")

        new_links = re.findall(r'href=[\'"]?([^\'" >]+)', get_response)

        # TODO search for hrefs and secret flags

    # connects to the web server
    def connect(self):
        self.client.connect((self.start, port))
        self.login()


def main():
    # Adds positional arguments for username and password
    parser = argparse.ArgumentParser(description="CS3700 Project 4 - Fakebook Web Crawler")
    parser.add_argument("username", nargs="+", type=str, action='store',
                        help="Your username for accessing the Fakebook site (your NU id with leading zeros)")
    parser.add_argument("password", nargs="+", type=str, action='store',
                        help="Your password for accessing the Fakebook site")
    args = parser.parse_args()

    # starts the web crawler
    WebCrawler(args.username[0], args.password[0], hostname).connect()


main()
