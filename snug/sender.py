"""tools for creating senders"""
from .core import Pipe, Sender, T_parsed, T_prepared, T_req, T_resp
from .utils import dclass, genresult


@dclass
class Piped(Sender[T_req, T_parsed]):
    """a sender wrapped with a pipe"""
    inner: Sender[T_prepared, T_resp]
    pipe:  Pipe[T_req, T_prepared, T_resp, T_parsed]

    def __call__(self, request):
        pipe = self.pipe(request)
        response = self.inner(next(pipe))
        return genresult(pipe, response)
