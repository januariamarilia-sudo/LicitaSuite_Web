class LicitaSuiteError(Exception):
    pass

class ZipValidationError(LicitaSuiteError):
    pass

class RequiredFileError(LicitaSuiteError):
    pass

class AppendixParserError(LicitaSuiteError):
    pass

class PdfParserError(LicitaSuiteError):
    pass

class DocxGenerationError(LicitaSuiteError):
    pass
