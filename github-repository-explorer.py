import os.path
import sys
import re
import requests
import time

print "touch STOP   to exit."
while not os.path.exists("STOP"):
  print "Getting task..."
  r = requests.post("http://tracker.archiveteam.org:8125/request?version=1&task=repos")
  if r.status_code == 404:
    print "No task. Waiting 10 seconds."
    time.sleep(10)

  elif r.status_code != 200:
    print "Received status code %d." % r.status_code
    print "Waiting 30 seconds."
    time.sleep(30)

  else:
    url = r.text

    print "GET %s" % url
    r = requests.get(url)
    if r.status_code != 200:
      print "Received status code %d." % r.status_code

      done = False
      while not done:
        print "Returning task..."
        r = requests.post("http://tracker.archiveteam.org:8125/return",
                          params={ "url": url })
        if r.status_code != 200:
          print "Tracker returned status code %d." % r.status_code
          print "Retrying after 30 seconds..."
          time.sleep(30)
        else:
          done = True

      print "Waiting 60 minutes."
      time.sleep(3600)

    else:
      print "OK! (Rate limit remaining: %s)" % r.headers["x-ratelimit-remaining"]
      data = r.content
      next_since = None
      if r.headers["link"]:
        m = re.search("since=([0-9]+)", r.headers["link"])
        if m:
          next_since = m.group(1)
          print "Next since: %s" % next_since

      done = False
      while not done:
        print "Submitting..."
        requests.post("http://tracker.archiveteam.org:8125/submit",
                      params={ "url": url, "next_url": "https://api.github.com/repositories?since=%s" % next_since },
                      data=data, headers={ "Content-Type": r.headers["content-type"] })
        if r.status_code != 200:
          print "Tracker returned status code %d." % r.status_code
          print "Retrying after 30 seconds..."
          time.sleep(30)
        else:
          done = True

