# PDM
from sonatoki.ilo import Ilo
from sonatoki.Tokenizers import (
    SentTokenizer,
    WordTokenizer,
    SentTokenizerRe,
    WordTokenizerRe,
    WordTokenizerRe1,
)


def dump_example(s: str):
    with open("examples.txt", "a+") as f:
        _ = f.write(s + "\n")


def test_sent_tokenizer(ilo: Ilo):
    for msg in fetch_discord():
        orig_msg = msg
        msg = ilo.preprocess(msg)
        sent_tok = SentTokenizer.tokenize(msg)
        sent_re = SentTokenizerRe.tokenize(msg)
        if sent_tok != sent_re:
            print("orig: %s" % msg)
            print("fnct: %s" % sent_tok)
            print("regx: %s" % sent_re)


def test_word_tokenizer(ilo: Ilo):
    for msg in fetch_discord():
        orig_msg = msg
        msg = ilo.preprocess(msg)
        fn_tokenized = WordTokenizer.tokenize(msg)
        re_tokenized = WordTokenizerRe.tokenize(msg)
        re1_tokenized = WordTokenizerRe1.tokenize(msg)
        if fn_tokenized != re1_tokenized:
            print("orig: %s" % msg)
            print("fnct: %s" % fn_tokenized)
            print("regx: %s" % re_tokenized)
            print("good: %s" % re1_tokenized)
            print()
