import enum

class ParsingReturnType(enum.Enum):
    LINK = 1
    FILES = 2
    METADATA = 3
    ALL = 4
    NONE = 5

class ZenodoErrorHandler:

    def parse_errors(response):
        print(response.json(), response)
        raise NameError("Something Failed with Zenodo")
    
    def parse_links(response):
        [print(key, response["metadata"]["links"][key]) for key in response["metadata"]["links"]]

    def parse_files(response):
        [print(f) for f in response["files"]]

    def parse_metadata(response):
        [print(key, response["metadata"][key]) for key in response["metadata"]]

    @staticmethod
    def parse(r, parsing_type=ParsingReturnType.NONE):

        if r.status_code >= 400:
            ZenodoErrorHandler.parse_errors(r)
        elif r.status_code == 204:
            return None
        else:
            response = r.json()
            if parsing_type == ParsingReturnType.LINK:
                ZenodoErrorHandler.parse_links(response)
            elif parsing_type == ParsingReturnType.FILES:
                ZenodoErrorHandler.parse_files(response)
            elif parsing_type == ParsingReturnType.METADATA:
                ZenodoErrorHandler.parse_metadata(response)
            elif parsing_type == ParsingReturnType.NONE:
                pass
            else:
                [print(key, response[key]) for key in response]
        
        # Always return id 
        return response["id"]
    