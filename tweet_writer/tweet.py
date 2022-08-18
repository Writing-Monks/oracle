class Tweet:
    def __init__(self, content: str, media_url: str, media_meta: dict):
        self.content = content
        self.media_url = media_url
        if media_url is not None:
            self.total_bytes = media_meta['totalBytes']
            self.mime_type = media_meta['mimeType']
        else:
            self.total_bytes = self.mime_type = None
