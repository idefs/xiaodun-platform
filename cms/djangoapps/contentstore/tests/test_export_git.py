"""
Test the ability to export courses to xml from studio
"""

import copy
import os
import shutil
import subprocess
from uuid import uuid4

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from pymongo import MongoClient

from .utils import CourseTestCase
import contentstore.git_export_utils as git_export_utils
from xmodule.contentstore.django import _CONTENTSTORE
from xmodule.modulestore.django import modulestore

TEST_DATA_CONTENTSTORE = copy.deepcopy(settings.CONTENTSTORE)
TEST_DATA_CONTENTSTORE['DOC_STORE_CONFIG']['db'] = 'test_xcontent_%s' % uuid4().hex


@override_settings(CONTENTSTORE=TEST_DATA_CONTENTSTORE)
class TestExportGit(CourseTestCase):
    """
    Tests pushing a course to a git repository
    """

    def setUp(self):
        """
        Setup test course, user, and url.
        """
        super(TestExportGit, self).setUp()
        self.course_module = modulestore().get_item(self.course.location)
        self.test_url = reverse('export_git', kwargs={
            'org': self.course.location.org,
            'course': self.course.location.course,
            'name': self.course.location.name,
        })

    def tearDown(self):
        MongoClient().drop_database(TEST_DATA_CONTENTSTORE['DOC_STORE_CONFIG']['db'])
        _CONTENTSTORE.clear()

    def test_giturl_missing(self):
        """
        Test to make sure an appropriate error is displayed
        if course hasn't set giturl.
        """
        response = self.client.get(self.test_url)
        self.assertEqual(200, response.status_code)
        self.assertIn(
            ('giturl must be defined in your '
             'course settings before you can export to git.'),
            response.content
        )

        response = self.client.get('{}?action=push'.format(self.test_url))
        self.assertEqual(200, response.status_code)
        self.assertIn(
            ('giturl must be defined in your '
             'course settings before you can export to git.'),
            response.content
        )

    def test_course_export_failures(self):
        """
        Test failed course export response.
        """
        self.course_module.giturl = 'foobar'
        modulestore().save_xmodule(self.course_module)

        response = self.client.get('{}?action=push'.format(self.test_url))
        self.assertIn('Export Failed:', response.content)

    def test_course_export_success(self):
        """
        Test successful course export response.
        """
        # Build out local bare repo, and set course git url to it
        repo_dir = os.path.abspath(git_export_utils.GIT_REPO_EXPORT_DIR)
        os.mkdir(repo_dir)
        self.addCleanup(shutil.rmtree, repo_dir)

        bare_repo_dir = '{0}/test_repo.git'.format(
            os.path.abspath(git_export_utils.GIT_REPO_EXPORT_DIR))
        os.mkdir(bare_repo_dir)
        self.addCleanup(shutil.rmtree, bare_repo_dir)

        subprocess.check_output(['git', '--bare', 'init', ], cwd=bare_repo_dir)

        self.populateCourse()
        self.course_module.giturl = 'file://{}'.format(bare_repo_dir)
        modulestore().save_xmodule(self.course_module)

        response = self.client.get('{}?action=push'.format(self.test_url))
        self.assertIn('Export Succeeded', response.content)
