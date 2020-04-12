CS3700 Project 4

Usage:
./webcrawler [username] [password]

Given a proper username and password, this web crawler will crawl the Fakebook site on fring.ccs.neu.edu and look for 
5 secret flags. It will print the flags as it finds them. 

Approach:

The first thing we tackled was connecting to the server via a TCP socket and sending a GET request for the Fakebook 
login page. After reading through the HTTP guide in the project description, this was quite trivial. After logging
in to my account on Google Chrome and carefully inspecting the request headers in the Network tab, we were able to 
figure out how to form the POST request and log in through our program. 

After requesting the main /fakebook/ page and finding all 'hrefs' in the html, we knew we would have to recursively
crawl to each site, find all of the Fakebook friends of each person, and visit their pages, repeating the process until
all flags were found. To do this, we made two functions to find all of the friends on the friends list of a certain
person. We did this by getting the links on the '/friends/1' page of each profile (if it exists), and then incrementing 
the 'friends' page number by one until all friends 'hrefs' have been found. We ignored the link to Northeastern's site
and the 'mailto'. 

After getting the list of all friends links, we would GET each page, look for links, and repeat the process, keeping
track of all the pages we have been to so that we don't waste time or enter a loop. For our GET method, we would 
request the given page, and then carefully inspect the response for several conditions. First, we would check
if the response contained a flag. If so, we print it and continue on until all 5 flags are found. Then, we checked
for 301, 403, 404, and 500 responses. If 301, we parse the response for the 'Location' header and send a new get
request for that new page. If a 403 or 404, we stop looking for that page. If a 500, we retry getting that page until 
we get a 200 OK response. 

This process of getting a profile page and then finding and getting all of its friends links continues until all 5
flags are found, after which we shutdown the socket connection and exit the program. 

Challenges:

1) Posting:  It took a little bit of time to figure out how to structure the POST header to include the required login 
information. After receiving the 302 Found, it also took a while for us to properly GET the /fakebook/ landing page,
because we forgot to terminate our GET request with a two new-lines.

2) Socket Disconnect: After beginning to crawl through the links on the Fakebook homepage, we discovered, after some
debugging, that we eventually we getting blank responses from the server. To handle this, in our get function, if the 
response from the server was an empty string, we would reconnect to the server and try sending our GET request again. 

3) Maximum Recursion Error: Another issue we ran into was Python's maximum recursive depth. Because we were essentially 
starting with the FIRST profile page, finding their friends, crawling through the FIRST friend and to find their
friends, and on and on, we eventually were getting over 1000 calls deep into to our crawl() function. To avoid this,
we set a maximum recursion depth of 200 calls and found that this was still sufficient enough to visit every page 
necessary. 

Testing:

We added print statements to test each step of our code. We checked to make sure we successfully connected to the 
socket, that we sucessfully logged in, that we found all links to a person's friends, that we skipped over 
pages we had already been to, that we caught and handled any non-200 responses from the server, and that we 
successfully found all 5 (or 10 combined) flags and successfully exited the program afterwards. 
