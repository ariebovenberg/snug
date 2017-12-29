import snug


def test_execute():
    sender = {'/posts/latest/': b'hello world'}.__getitem__

    class MyQuery:
        def __resolve__(self):
            return (yield '/posts/latest/').decode('ascii')

    assert snug.execute(sender, MyQuery()) == 'hello world'
