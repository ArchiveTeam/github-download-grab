import time
import os
import os.path
import functools
import shutil
import glob
import json
from distutils.version import StrictVersion

from tornado import gen, ioloop
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

import seesaw
from seesaw.project import *
from seesaw.config import *
from seesaw.item import *
from seesaw.task import *
from seesaw.pipeline import *
from seesaw.externalprocess import *
from seesaw.tracker import *


if StrictVersion(seesaw.__version__) < StrictVersion("0.0.10"):
  raise Exception("This pipeline needs seesaw version 0.0.10 or higher.")


USER_AGENT = "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/533.20.25 (KHTML, like Gecko) Version/5.0.4 Safari/533.20.27"
VERSION = "20121213.01"

class PrepareDirectories(SimpleTask):
  def __init__(self):
    SimpleTask.__init__(self, "PrepareDirectories")

  def process(self, item):
    item_name = item["item_name"]
    dirname = "/".join(( item["data_dir"], item_name ))

    if os.path.isdir(dirname):
      shutil.rmtree(dirname)

    os.makedirs(dirname + "/files")

    item["item_dir"] = dirname

    os.makedirs(dirname + ("/files/github.com/downloads/%s" % item["item_name"]))

class RecursivePrepareStatsForTracker(SimpleTask):
  def __init__(self, defaults=None, file_groups=None, id_function=None):
    SimpleTask.__init__(self, "PrepareStatsForTracker")
    self.defaults = defaults or {}
    self.file_groups = file_groups or {}
    self.id_function = id_function

  def process(self, item):
    total_bytes = {}
    for (group, files) in self.file_groups.iteritems():
      total_bytes_group = 0
      for f in files:
        for f_root, f_dirs, f_files in os.walk(realize(f, item)):
          total_bytes_group += sum([ os.path.getsize(os.path.join(f_root, name)) for name in f_files ])
      total_bytes[group] = total_bytes_group

    stats = {}
    stats.update(self.defaults)
    stats["item"] = item["item_name"]
    stats["bytes"] = total_bytes

    if self.id_function:
      stats["id"] = self.id_function(item)

    item["stats"] = realize(stats, item)

def calculate_item_id(item):
  return "%d" % item["file_count"]


class MakeIndexFile(SimpleTask):
  def __init__(self):
    SimpleTask.__init__(self, "MakeIndexFile")

  def process(self, item):
    with open(os.path.join(item["item_dir"], "files/github.com/ArchiveTeam/mobileme-grab/downloads.html")) as f:
      html = f.read()
    
    with open(os.path.join(item["item_dir"], "files/github.com/downloads/ArchiveTeam/mobileme-grab/index.txt"), "w") as f:
      f.write("file\tuploaded\tdownloads\n")
      file_count = 0
      for filename, uploaded, downloads in re.findall(r'"/downloads/([^"]+)">.+?datetime="([^"]+)".+?<strong>([0-9,]+)</strong> down', html, re.DOTALL):
        downloads = re.sub("[^0-9]+", "", downloads)
        f.write("\t".join((filename, uploaded, downloads)) + "\n")
        file_count += 1
        item["file_count"] = file_count


project = Project(
  title = "GitHub downloads",
  project_html = """
    <img class="project-logo" alt="GitHub logo" src="http://archiveteam.org/images/thumb/f/fd/Github-logo-v7.png/120px-Github-logo-v7.png" />
    <h2>GitHub downloads <span class="links"><a href="https://github.com/">Website</a> &middot; <a href="http://tracker.archiveteam.org/github/">Leaderboard</a></span></h2>
    <p><i>GitHub</i> is disabling its Downloads section. We make a copy.</p>
  """,
  utc_deadline = datetime.datetime(2013,03,10, 23,59,0)
)

pipeline = Pipeline(
  GetItemFromTracker("http://tracker.archiveteam.org/github", downloader, VERSION),
  PrepareDirectories(),
  WgetDownload([ "./wget-lua",
      "-U", USER_AGENT,
      "-nv",
      "-o", ItemInterpolation("%(item_dir)s/wget.log"),
      "--no-check-certificate",
      "--directory-prefix", ItemInterpolation("%(item_dir)s/files"),
      "--force-directories",
      "--adjust-extension",
      "-e", "robots=off",
      "--span-hosts",
      "--lua-script", "github-downloads.lua",
      "--timeout", "60",
      "--tries", "20",
      "--waitretry", "5",
      ItemInterpolation("https://github.com/%(item_name)s/downloads")
    ],
    max_tries = 2,
    accept_on_exit_code = [ 0, 4, 6, 8 ],
  ),
  MakeIndexFile(),
  PrepareStatsForTracker(
    defaults = { "downloader": downloader, "version": VERSION },
    file_groups = {
      "data": [ ItemInterpolation("%(item_dir)s/files/github.com/downloads/") ]
    },
    id_function = calculate_item_id
  ),
  LimitConcurrent(NumberConfigValue(min=1, max=4, default="1", name="shared:rsync_threads", title="Rsync threads", description="The maximum number of concurrent uploads."),
    RsyncUpload(
      target = ConfigInterpolation("fos.textfiles.com::alardland/warrior/github/%s/", downloader),
      target_source_path = ItemInterpolation("%(item_dir)s/files/"),
      files = [
        ItemInterpolation("%(item_dir)s/files/github.com/downloads/")
      ],
      extra_args = [
        "--recursive",
        "--partial",
        "--partial-dir", ".rsync-tmp"
      ]
    ),
  ),
  SendDoneToTracker(
    tracker_url = "http://tracker.archiveteam.org/github",
    stats = ItemValue("stats")
  )
)

