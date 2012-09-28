#!/usr/bin/python2.6
# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests validity of the apiserving/libgen/gen configuration files.

This looks at the contents of the config files used by the code generator
to make sure they won't blow up at run time.
"""

__author__ = 'aiuto@google.com (Tony Aiuto)'

import json
import os
import re

from google.apputils import basetest
from googleapis.codegen import platforms
from googleapis.codegen.json_expander import ExpandJsonTemplate


class ConfigurationTest(basetest.TestCase):

  _SRC_DATA_DIR = os.path.dirname(__file__)

  @staticmethod
  def WalkFileTree(pattern, root=_SRC_DATA_DIR):
    """Walk the source file tree and return file paths matching the pattern.

    Args:
      pattern: (str) A regex for a file pattern.
      root: (str) root of search tree.
    Yields:
      (str) list of path names
    """
    # Walk tree for jar files to directly include
    matcher = re.compile(pattern)
    for root, unused_dirs, file_names in os.walk(root):
      for file_name in file_names:
        if matcher.match(file_name):
          yield os.path.join(root, file_name)

  def LoadJsonFile(self, path, expand=False):
    """Loads a file but ignores the broken ones.

    Fails a test assertion if the file is not loadable.

    Args:
      path: (str) path to file.
      expand: (bool, default False) whether to expand as a Json template.
    Returns:
      (dict) or None if the file is in a white list of known broken files.
    """
    json_file = open(path)
    content = json_file.read()
    self.assertLess(1, len(content))
    json_file.close()
    try:
      json_data = json.loads(content)
    except ValueError as err:
      # Ignore the known broken files.
      if not path.endswith('testdata/broken.json'):
        self.fail('%s: %s' % (path, err))
      return None
    if expand:
      json_data = ExpandJsonTemplate(json_data)
    return json_data

  def testCheckAllJsonFiles(self):
    for path in self.WalkFileTree('.*\.json$'):
      json_data = self.LoadJsonFile(path)
      if json_data:
        self.assertTrue(isinstance(json_data, dict))

  def testCheckAllFeaturesFiles(self):
    """Make sure the features.json files obey the rules."""

    def CheckFileContent(path, json_data):

      def HasElement(e):
        if json_data.get(e) is None:
          self.fail('%s: is missing "%s"' % (path, e))
      HasElement('description')
      HasElement('releaseVersion')
      language = json_data.get('language')
      possible_environments = set(platforms.PLATFORMS[platforms.ALL])
      if language:
        for p in platforms.PLATFORMS.get(language, []):
          possible_environments.add(p)

      for r in json_data.get('requires', []):

        def HasRequiresElement(d, e):
          if d.get(e) is None:
            self.fail('%s: "requires" item is missing "%s"' % (path, e))
        HasRequiresElement(r, 'name')
        HasRequiresElement(r, 'version')
        HasRequiresElement(r, 'environments')
        environments = r['environments']
        for e in environments:
          if not e in possible_environments:
            self.fail('%s: bad environment list: %s in %s'
                      % (path, environments, r))
        for f in r.get('files', []):
          file_type = f['type']
          if file_type not in platforms.FILE_TYPES[platforms.ALL]:
            self.fail('%s: unknown file type %s in %s' % (path, file_type, r))

    for path in self.WalkFileTree('features\.json$'):
      json_data = self.LoadJsonFile(path, True)
      if json_data:
        CheckFileContent(path, json_data)

  def testCheckDependenciesExist(self):
    # Test that the file actually exist.
    for path in self.WalkFileTree('features\.json$'):
      # Skip this check for test files.
      if path.find('/testdata/') >= 0:
        continue
      json_data = self.LoadJsonFile(path, True)
      if not json_data:
        continue
      language = json_data.get('language')
      if not language:
        continue
      # Skip this check for 'default' versions of language surface. Those don't
      # get used in the service, so they done need dependencies
      if path.find('%s/default' % language) >= 0:
        continue

      features_dir = os.path.dirname(path)
      for r in json_data.get('requires', []):
        for f in r.get('files', []):
          file_path = f.get('path')
          if file_path:
            p = os.path.join(features_dir, 'dependencies', file_path)
            self.assertTrue(os.path.exists(p), '%s not found' % p)


if __name__ == '__main__':
  basetest.main()