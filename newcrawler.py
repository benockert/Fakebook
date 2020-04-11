# CS3700 Networks and Distributed Systems - Project 4
import argparse
import socket
import re
from time import sleep

# GLOBALS
VERSION = "HTTP/1.1"
GET = "GET"
POST = "POST"
ROOT = "/fakebook/"
LOGIN = "/accounts/login/?next=/fakebook/"
FLAG = "class='secret_flag' style=\"color:red\">FLAG:"

# Socket connection information
hostname = "fring.ccs.neu.edu"
port = 80

# POST header for the initial login sequence
post_header = POST + " " + LOGIN + " " + VERSION + "\nHost: %s\nCookie: " % hostname
get_header = GET + " " + ROOT + " " + VERSION + "\nHost: %s\nCookie: " % hostname

# List of explored pages
explored = ['http://www.northeastern.edu', 'mailto:cbw@ccs.neu.edu']
# Filter for non-domain pages
non_domain = ['/fakebook/', 'http://www.northeastern.edu', 'mailto:cbw@ccs.neu.edu']

# Secret flags
flags = []


class WebCrawler(object):

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.csrf = ''
        self.sessionid = ''
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    ###########################GETS THE REQUEST PAGE AND LOOKS FOR FLAGS AND EXCEPTIONS################################
    # TODO
    # gets the requested page, checking for errors and flags, and updating the explored pages
    def get_page(self, page):
        print("Getting: ", page)
        # forms the get request with the given page url
        get = (GET + " " + page + " " + VERSION + "\nHost: " + hostname + "\nCookie: " +
               "csrftoken=" + self.csrf + "; sessionid=" + self.sessionid + '\n\n')

        # sends and recieves from the socket
        self.client.send(get.encode())
        sleep(.1)
        response = self.client.recv(4096).decode("latin-1")

        # after receiving a response, adds the link to the explored page
        explored.append(page)

        # looks for flags in the server response
        flag_mark = response.find(FLAG)
        if flag_mark != -1:
            print("Found FLAG")
            secret_flag = response[flag_mark+43:flag_mark+107]
            flags.append(secret_flag)

        # handles errors sent by the server; returns the response once successful
        moved_error = response.find(VERSION + " 301")
        forbidden_error = response.find(VERSION + " 403")
        not_found_error = response.find(VERSION + " 404")
        internal_error = response.find(VERSION + " 500")
        if moved_error != -1:
            print("301 Redirect")
            location_start = response.find("Location:")
            location_end = response.find("Content-Length")
            new_location = response[location_start + 10:location_end - 2]
            self.get_page(new_location)
        elif forbidden_error != -1 or not_found_error != -1:
            print("403/4 Not Found")
            return None
        elif internal_error != -1:
            print("500 Internal")
            self.get_page(page)
        else:
            return response

    ###################################################################################################################
    ##########################CRAWLS THROUGH LISTS OF PAGES AND FINDS NEW LINKS TO FRIENDS#############################
    # gets the list of hrefs to the given profile's friends (may be empty i.e. no friends)
    def get_friends(self, profile):
        friends = []

        main_profile_page = self.get_page(profile)

        # if there is a response (i.e. not a 404), parse and look for links
        if main_profile_page:
            hrefs = re.findall(r'href=[\'"]?([^\'" >]+)', main_profile_page)
            # if there is a friends list, get the list of names
            # HARD CODED ASSUMPTION!!!!
            if len(hrefs) > 2 and '/friends/' in hrefs[2]:
                friends_links = re.findall(r'href=[\'"]?([^\'" >]+)', str(self.get_page(hrefs[2])))
                for link in friends_links:
                    if 'friends' not in link and link not in non_domain:
                        friends.append(link)

        # link to friends page
        return friends

    # TODO
    # crawls through a list of profiles, looking for new links and flags
    def crawl(self, list_of_friends):
        for href in list_of_friends:
            print(str(len(list_of_friends)))
            if href in explored:
                print("Already explored")
                continue
            else:
                # gets the links to all of the current person's friends (and makes sure they have them)
                links = self.get_friends(href)
                if len(links) == 0:
                    continue
                self.crawl(links)

    ###################################################################################################################
    ##################################LOGIN AND BEGIN CRAWLING ON HOME PAGE PROFILES###################################
    # after logging in, get the root page's html (/fakebook/)
    def get_root(self):
        # get request for the root page with the login sessionid included
        get_request = get_header + "csrftoken=" + self.csrf + "; sessionid=" + self.sessionid + '\n\n'
        self.client.send(get_request.encode())

        # gets the server's response (html of the root webpage) and the href links
        root_response = self.client.recv(4096).decode("latin-1")

        root_links = re.findall(r'href=[\'"]?([^\'" >]+)', root_response)
        for link in root_links:
            if link[0:10] != "/fakebook/" or link in explored:
                root_links.remove(link)

        self.crawl(root_links)

    # logs in to Fakebook
    def login(self):
        # GETS the html of the login page
        request = GET + " " + LOGIN + " " + VERSION + "\nHost:%s\n\n" % hostname
        self.client.send(request.encode())

        # gets the server's response (html of the webpage)
        response = self.client.recv(4096).decode("latin-1")
        explored.append(LOGIN)

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

        if post_response.find("302 FOUND") != -1:
            print("LOGIN SUCCESSFUL")
        else:
            print("LOGIN FAILED")

        new_id_start = post_response.find('sessionid=') + 10
        self.sessionid = post_response[new_id_start:new_id_start + 32]

        # calls the function to get the html of the main Fakebook page
        explored.append(ROOT)
        self.get_root()

    # connects to the web server
    def connect(self):
        self.client.connect((hostname, port))
        self.login()
        print(explored)
    ###################################################################################################################


def main():
    # Adds positional arguments for username and password
    parser = argparse.ArgumentParser(description="CS3700 Project 4 - Fakebook Web Crawler")
    parser.add_argument("username", nargs="+", type=str, action='store',
                        help="Your username for accessing the Fakebook site (your NU id with leading zeros)")
    parser.add_argument("password", nargs="+", type=str, action='store',
                        help="Your password for accessing the Fakebook site")
    args = parser.parse_args()

    # starts the web crawler
    crawler = WebCrawler(args.username[0], args.password[0])
    crawler.connect()

    # prints the secret flags
    print(flags)


main()
