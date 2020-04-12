# CS3700 Networks and Distributed Systems - Project 4
import argparse
import socket
import re
from time import sleep

# Globals
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

# a list to store the secret flags
flags = []


# called to connect to the fring.ccs.neu.edu server
def connect():
    global client
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((hostname, port))


# called after all flags are received; shutsdown the socket connection and ends the program
def disconnect():
    global client
    client.shutdown(1)
    client.close()
    exit(0)


class WebCrawler(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.csrf = ''
        self.sessionid = ''

    # gets the requested page, checking for errors and flags, and updating the explored pages
    def get_page(self, page):
        # forms the get request with the given page url
        get = (GET + " " + page + " " + VERSION + "\nHost: " + hostname + "\nCookie: " +
               "csrftoken=" + self.csrf + "; sessionid=" + self.sessionid + '\n\n')

        # sends and recieves from the socket
        client.sendall(get.encode())
        sleep(.05)
        response = client.recv(4096).decode("latin-1")

        # if there is no response, reconnects to the server and resends the get request
        if response == "":
            connect()
            client.sendall(get.encode())
            sleep(.1)
            response = client.recv(4096).decode("latin-1")

        # after receiving a response, adds the link to the explored page
        explored.append(page)

        # looks for flags in the server response
        flag_mark = response.find(FLAG)
        if flag_mark != -1:
            secret_flag = response[flag_mark + 44:flag_mark + 108]
            # if found, prints the flag, adds it to the list, and checks if all 5 have been found
            print(secret_flag)
            flags.append(secret_flag)
            # if all 5 flags have been found, disconnect and end the program
            if len(flags) == 5:
                disconnect()

        # handles errors sent by the server; returns the response once successful
        moved_error = response.find(VERSION + " 301")
        forbidden_error = response.find(VERSION + " 403")
        not_found_error = response.find(VERSION + " 404")
        internal_error = response.find(VERSION + " 500")
        # if a page has been moved, parses the response to find the new location, and gets the new page
        if moved_error != -1:
            location_start = response.find("Location:")
            location_end = response.find("Content-Length")
            new_location = response[location_start + 10:location_end - 2]
            return self.get_page(new_location)
        # if Forbidden or Not Found, returns None
        elif forbidden_error != -1 or not_found_error != -1:
            return None
        # if there is a server-side error, attempts to get the same page again until success
        elif internal_error != -1:
            return self.get_page(page)
        # when a 200 OK response is received, returns the response
        else:
            return response

    # recursively gets all x-number of friends list pages
    def get_all_friends(self, friends_list, page_num):
        all_friends = []

        this_page = friends_list + str(page_num) + "/"

        # determines what the link of the next friends list page would be, if it exists
        next_page_num = page_num + 1
        next_page = friends_list + str(next_page_num) + "/"

        friends_links = re.findall(r'href=[\'"]?([^\'" >]+)', str(self.get_page(this_page)))
        for link in friends_links:
            # ignores links to non-fakebook pages and other pages of this user's friends
            if 'friends' not in link and link not in non_domain:
                all_friends.append(link)

        # looks to see if there is another page of friends, if so it gets those friends
        if next_page in friends_links:
            all_friends.extend(self.get_all_friends(friends_list, next_page_num))

        return all_friends

    # gets the list of hrefs to the given profile's friends (may be empty i.e. no friends)
    def get_friends(self, profile):
        friends = []

        # gets the main profile page of the given user page; returns None if no such page exists
        main_profile_page = self.get_page(profile)

        # if there is a response (i.e. not a 403/4), parse and look for links
        if main_profile_page:
            hrefs = re.findall(r'href=[\'"]?([^\'" >]+)', main_profile_page)
            # if there is a friends list, get the list of names
            if len(hrefs) > 2 and '/friends/' in hrefs[2]:
                # gets all of the friends of the given person, beginning with friends list page 1
                friends.extend(self.get_all_friends(hrefs[2][0:-2], 1))

        # links to all friends pages
        return friends

    # crawls through the given list of profiles
    def crawl(self, list_of_friends, depth):
        for href in list_of_friends:
            # sets a maximum recursion depth of 200 calls
            if depth >= 200:
                break
            # checks to see if the current href has already been explored
            if href in explored:
                continue
            else:
                # gets the links to all of the current person's friends (and makes sure they have them)
                links = self.get_friends(href)
                if len(links) == 0:
                    continue
                self.crawl(links, depth + 1)

    # after logging in, get the root page's html (/fakebook/)
    def get_root(self):
        # get request for the root page with the login sessionid included
        get_request = get_header + "csrftoken=" + self.csrf + "; sessionid=" + self.sessionid + '\n\n'
        client.send(get_request.encode())

        # gets the server's response (html of the root webpage) and the href links
        root_response = client.recv(4096).decode("latin-1")
        root_links = re.findall(r'href=[\'"]?([^\'" >]+)', root_response)

        # looks through the links on the root page and removes them if they have already been explored
        for link in root_links:
            if link[0:10] != "/fakebook/" or link in explored:
                root_links.remove(link)

        # begins the crawl through Fakebook, starting with the links on the main landing page
        self.crawl(root_links, 1)

    # logs in to Fakebook with the username and password given as inputs to the program
    def login(self):
        # GETS the html of the login page
        request = GET + " " + LOGIN + " " + VERSION + "\nHost:%s\n\n" % hostname
        client.send(request.encode())

        # gets the server's response (html of the webpage)
        response = client.recv(4096).decode("latin-1")
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

        client.send(post.encode())

        # gets the server's response to the post
        post_response = client.recv(4096).decode("latin-1")

        if post_response.find("302 FOUND") == -1:
            print("LOGIN FAILED...please re-run the program")
            exit(1)

        # looks for the next session id returned by the server
        new_id_start = post_response.find('sessionid=') + 10
        self.sessionid = post_response[new_id_start:new_id_start + 32]

        # calls the function to get the html of the main Fakebook page
        explored.append(ROOT)
        self.get_root()


def main():
    # Adds positional arguments for username and password
    parser = argparse.ArgumentParser(description="CS3700 Project 4 - Fakebook Web Crawler")
    parser.add_argument("username", nargs="+", type=str, action='store',
                        help="Your username for accessing the Fakebook site (your NU id with leading zeros)")
    parser.add_argument("password", nargs="+", type=str, action='store',
                        help="Your password for accessing the Fakebook site")
    args = parser.parse_args()

    # created a web crawler with the given username and password
    crawler = WebCrawler(args.username[0], args.password[0])
    # connects to the Fakebook server
    connect()
    # logs into the server and begins crawling through the site
    crawler.login()


main()
