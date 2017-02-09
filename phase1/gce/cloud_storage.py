#! /usr/bin/python
"""This library will manage files stored in google cloud storage.
Since many files are produced when clusters are created, we need
to retain them so we can use them across container instances.
"""
import os
import sys
import re

import argparse

from google.cloud import storage

GOOGLE_APPLICATION_CREDENTIALS = 'GOOGLE_APPLICATION_CREDENTIALS'
CLUSTER_NAME = 'CLUSTER_NAME'


def main():
    """Parse command line and run the appropriate method"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--upload', action='store_true', help='Upload cluster config files to GCS bucket')
    parser.add_argument('--download', action='store_true', help='Download cluster config files from GCS bucket')
    parser.add_argument('--clean', action='store_true', help='Remove cluster config files from GSC bucket')

    if len(sys.argv) != 2:
        parser.print_help()
        sys.exit(1)

    try:
        options = parser.parse_args()
    except:
        parser.print_help()
        sys.exit(0)

    if options.upload:
        CloudStorage().files_up()

    elif options.download:
        CloudStorage().files_down()

    elif options.clean:
        CloudStorage().delete_files_from_bucket()

    else:
        # should never get here...
        parser.print_help()
        sys.exit(1)


class CloudStorage(object):
    """Use this class to send files up or get files from google cloud storage"""

    def __init__(self):

        self.cwd = os.path.dirname(os.path.realpath(__file__))
        self.tmp = '{}/.tmp'.format(self.cwd)
        self.root = self.cwd.replace('/phase1/gce', '')

        # We make sure the GOOGLE_APPLICATION_CREDENTIALS env var is set.
        # If it is not, we set it to self.cwd/account.json

        credentials = os.environ.get(GOOGLE_APPLICATION_CREDENTIALS)
        if not credentials:
            account_json = '{}/account.json'.format(self.cwd)
            if os.path.isfile(account_json):
                os.environ[GOOGLE_APPLICATION_CREDENTIALS] = account_json
                self._print('Loading creds from {}'.format(account_json))
            else:
                msg = 'Missing Environment Variable {} and default file {} not found'.format(
                    GOOGLE_APPLICATION_CREDENTIALS, account_json)
                self._print_err(msg)

        self.storage_client = storage.Client()
        if not self.storage_client:
            self._print_err('Could not get google cloud storage client')

        # verify that the ENV for cluster_name is set. We use that for folder.
        cluster_name = os.environ.get(CLUSTER_NAME)
        if not cluster_name:
            self._print_err('Missing env var {}'.format(CLUSTER_NAME))
        self.cluster_name = self._cleanse_name(cluster_name)

        self.bucket = self._get_bucket()

    def _get_bucket(self):
        """The bucket name should be <project>-applariat-cluster-data.
        A '.' cannot be used in the name or it will require proper DNS."""

        project = self._cleanse_name(self.storage_client.project)
        bucket_name = '{}-applariat-cluster-data'.format(project)

        bucket = self.storage_client.lookup_bucket(bucket_name)
        if not bucket:
            bucket = self.storage_client.create_bucket(bucket_name)
            self._print('Bucket {} created.'.format(bucket.name))
        else:
            self._print('Bucket {} found.'.format(bucket.name))

        return bucket

    def _upload_blob(self, file):
        """Uploads a file to the bucket. Use the cluster_name as folder"""
        source_file_name = '{}/{}'.format(self.root, file)
        destination_name = '{}/{}'.format(self.cluster_name, file)
        blob = self.bucket.blob(destination_name)
        blob.upload_from_filename(source_file_name)

        self._print('Uploading {} -> {}/{}'.format(source_file_name, self.bucket.name, destination_name))

    @staticmethod
    def _cleanse_name(name):
        """Allow only num/char/-/_ in names. Periods will be removed due to DNS issue"""
        return re.sub(r'^[a-zA-Z0-9-_]$', '', name)

    @staticmethod
    def _print_err(msg):
        print 'ERROR: {}'.format(msg)
        exit(1)

    @staticmethod
    def _print(msg):
        print 'STORAGE: {}'.format(msg)

    def files_up(self):
        """Upload all required files"""

        # root files
        self._upload_blob('.config')
        self._upload_blob('.config.json')

        # phase1/gce files
        self._upload_blob('phase1/gce/terraform.tfstate')
        self._upload_blob('phase1/gce/terraform.tfstate.backup')

        # phase1/gce/.tmp files, some names are generated so it is easier to loop
        for _, _, tmp_files in os.walk(self.tmp):
            for tmp_file in tmp_files:
                f = '{}/{}'.format('phase1/gce/.tmp', tmp_file)
                self._upload_blob(f)

    def files_down(self):
        """Downloads all files to local system. Puts them where they belong"""

        if not os.path.exists(self.tmp):
            os.makedirs(self.tmp)

        blobs = self.bucket.list_blobs(prefix=self.cluster_name)
        for blob in blobs:
            # Need to replace cluster_name folder with cwd
            destination_file_name = blob.name.replace(self.cluster_name, self.root, 1)
            blob.download_to_filename(destination_file_name)
            self._print('Downloaded {}'.format(destination_file_name))

    def delete_files_from_bucket(self):
        """Remove the folder that contains all cluster information"""

        blobs = self.bucket.list_blobs(prefix=self.cluster_name)
        for blob in blobs:
            self._print('Deleting {}/{}'.format(self.bucket.name, blob.name))
            self.bucket.delete_blob(blob.name)


if __name__ == '__main__':
    main()