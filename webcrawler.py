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
post_header = POST + LOGIN + VERSION + "\nHost: %s\nConnection: keep-alive\nCookie: " % hostname
get_header = GET + ROOT + VERSION + "\nHost: %s\nCookie: " % hostname

# Secret flags
flags = []


class WebCrawler(object):

    def __init__(self, username, password, start_url):
        self.username = username
        self.password = password
        self.start = start_url
        self.csrf = ''
        self.sessionid = ''
        self.explored = []
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # returns the html of the given webpage
    def get(self, page):
        # forms the get request with the given page url
        get = (GET + " " + page + " " + VERSION + "\nHost: " + hostname + "\nCookie: " +
               "csrftoken=" + self.csrf + "; sessionid=" + self.sessionid + '\n\n')

        # sends and recieves from the socket
        self.client.send(get.encode())
        response = self.client.recv(4096).decode("latin-1")

        # handles errors sent by the server; returns the response once successful
        moved_error = response.find("301")
        forbidden_error = response.find("403 FORBIDDEN")
        not_found_error = response.find("404 Page Not Found")
        internal_error = response.find("500 INTERNAL SERVER ERROR")
        if moved_error != -1:
            #print("\n\n\n\n\n\n\n\n\n301 MOVED PERMANENTLY\n\n\n\n\n\n\n\n")
            pass
        elif forbidden_error != -1 or not_found_error != -1:
            print("\n\n\n\n\n\n\n\n\n404 NOT FOUND\n\n\n\n\n\n\n\n")
            return None
        elif internal_error != -1:
            #print("\n\n\n\n\n\n\n\n\nINTERNAL\n\n\n\n\n\n\n\n\n\n")
            return self.get(page)
        else:
            self.explored.append(page)
            #print(response)
            return response

    # logs in to Fakebook
    def login(self):
        # GETS the html of the login page
        request = GET + LOGIN + VERSION + "\nHost:%s\n\n" % self.start
        self.client.send(request.encode())

        # gets the server's response (html of the webpage)
        response = self.client.recv(4096).decode("latin-1")
        self.explored.append(LOGIN[1:len(LOGIN) - 1])

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

        # calls the function to get the html of the main Fakebook page
        self.get_root()

    # after logging in, get the root page's html (/fakebook/)
    def get_root(self):
        # get request for the root page with the login sessionid included
        get_request = get_header + "csrftoken=" + self.csrf + "; sessionid=" + self.sessionid + '\n\n'
        self.client.send(get_request.encode())

        # gets the server's response (html of the root webpage) and the href links
        root_response = self.client.recv(4096).decode("latin-1")
        self.explored.append(ROOT[1:len(ROOT) - 1])
        links = re.findall(r'href=[\'"]?([^\'" >]+)', root_response)
        print(links)
        self.crawl_list(links)

    # returns a list of profile links of all friends of the given person that we have not yet explored
    def get_friends(self, link):
        friends_href = []

        html = self.get(link)
        friends = html.findall(r'href=[\'"]?([^\'" >]+)')

        # gets all of the unexplored friends of the given profile
        for friend in friends:
            if friend.find("/friends") == -1 and friend[0:10] == "/fakebook/" and friend not in self.explored:
                friends_href.append(friend)
            else:
                if friend[0:10] == "/fakebook/" and friend not in self.explored:
                    friends_href += self.get_friends(friend)

        return friends_href

    # crawls over the given list of linked profile pages
    def crawl_list(self, href_list):

        for profile in href_list:
            if profile[0:10] == "/fakebook/" and profile not in self.explored:
                print(profile)
                self.crawl(profile)

    def crawl(self, href):
        # GETs the given profile page and looks for flags and hrefs
        html = self.get(href)

        flag = html.find("FLAG:")
        if flag != -1:
            secret_flag = html[flag + 6:flag + 71]
            flags.append(secret_flag)

        # gets the list of all friends who have not been visited yet
        unexp_friends = self.get_friends(href + "friends/1/")
        print(unexp_friends)

        #self.crawl_list(friends)

    # connects to the web server
    def connect(self):
        self.client.connect((self.start, port))
        self.login()

    def get_explored(self):
        return self.explored


def main():
    # Adds positional arguments for username and password
    parser = argparse.ArgumentParser(description="CS3700 Project 4 - Fakebook Web Crawler")
    parser.add_argument("username", nargs="+", type=str, action='store',
                        help="Your username for accessing the Fakebook site (your NU id with leading zeros)")
    parser.add_argument("password", nargs="+", type=str, action='store',
                        help="Your password for accessing the Fakebook site")
    args = parser.parse_args()

    # starts the web crawler
    crawler = WebCrawler(args.username[0], args.password[0], hostname)
    crawler.connect()

    print(flags)


main()
