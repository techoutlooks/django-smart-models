import logging


class NestingErrorException(Exception):
    """
    Simply re-raise original exception after
    enabling more verbose (`msg ` argument passed on) and logging the error.
    """
    # FIXME: subclass `rest_framework.APIException` instead.
    # TODO: add python2 compat:
    # https://stackoverflow.com/questions/18188563/how-to-re-raise-an-exception-in-nested-try-except-blocks
    def __init__(self, msg=None, *args, **kwargs):
        logging.error("WritableNestingModelSerializerMixin.{}".format(msg))
        super(NestingErrorException, self).__init__(*args, **kwargs)
