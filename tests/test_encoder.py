from unittest.mock import patch

from tdt.dados.encoder import criar_encoder


def test_criar_encoder_aceita_device_none_sem_quebrar():
    with patch("tdt.dados.encoder.SentenceTransformer") as MockST:
        MockST.return_value.encode.return_value = [[0.1, 0.2]]
        encode = criar_encoder("modelo-fake", device=None)
        encode(["texto"])
        MockST.assert_called_once_with("modelo-fake", device=None)


def test_criar_encoder_propaga_device_explicito():
    with patch("tdt.dados.encoder.SentenceTransformer") as MockST:
        MockST.return_value.encode.return_value = [[0.1, 0.2]]
        encode = criar_encoder("modelo-fake", device="cuda")
        encode(["texto"])
        MockST.assert_called_once_with("modelo-fake", device="cuda")
