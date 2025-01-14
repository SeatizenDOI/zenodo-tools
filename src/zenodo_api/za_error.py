import enum
from requests import Response

class ParsingReturnType(enum.Enum):
    LINK = 1
    FILES = 2
    METADATA = 3
    ALL = 4
    NONE = 5

class ZenodoErrorHandler:

    @staticmethod
    def parse_errors(response) -> None:
        print(response)
        raise NameError("Something Failed with Zenodo")
    
    @staticmethod
    def parse_links(response) -> None:
        [print(key, response["metadata"]["links"][key]) for key in response["metadata"]["links"]]

    @staticmethod
    def parse_files(response) -> None:
        [print(f) for f in response["files"]]

    @staticmethod
    def parse_metadata(response) -> None:
        [print(key, response["metadata"][key]) for key in response["metadata"]]

    @staticmethod
    def parse(r: Response, parsing_type=ParsingReturnType.NONE) -> int | None:

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
    