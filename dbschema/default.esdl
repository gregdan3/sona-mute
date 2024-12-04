module default {
  type Platform {
    required _id: int16;  # if there are ever more than 2^16 platforms, what
    required name: str;

    constraint exclusive on ((._id));
    index on ((._id));
  }

  type Community {
    required _id: bigint;
    name: str;
    required platform: Platform;

    multi messages := .<community[is Message];
    multi user_messages := (select .<community[is Message] filter .is_counted);

    constraint exclusive on ((._id, .platform));
    index on ((._id, .platform));
  }

  type Author {
    required _id: bigint;
    name: str;
    required platform: Platform;
    required is_bot: bool;
    required is_webhook: bool;

    multi messages := .<author[is Message];
    multi user_messages := (select .<author[is Message] filter .is_counted);
    num_tp_sentences: int64 {
      default := 0;
    };
    constraint exclusive on ((._id, .name, .platform));
    index on ((._id, .platform));
  }

  type Sentence {
    required message: Message;
    required words: array<str>;
    required score: float64;
    # NOTE: Will be pre-tokenized with the **toki pona** tokenizer,
    # and pre-cleaned by removing consecutive duplicates.

    index on ((.score));
  }

  type Message {
    required _id: bigint;
    required community: Community;
    required container: bigint;
    # if there is some further level of organization, put it here
    # e.g. discord channels, reddit flairs
    # user must specify as 0 if "null"
    required author: Author;
    required postdate: datetime;
    required content: str;
    required is_counted: bool;
    # simplified from checking the author's is_bot or is_webhook
    # or containers of the message

    multi sentences := .<message[is Sentence];
    multi tp_sentences := (select .<message[is Sentence] filter .score >= 0.8);

    constraint exclusive on ((._id, .community));
    index on ((._id, .community));
    index on ((.is_counted, .postdate));
  }

  alias TPUserSentence := (
    SELECT Sentence FILTER
      .score >= 0.8 AND
      .message.is_counted
  );

  alias NonTPUserSentence := (
    SELECT Sentence FILTER
      .score < 0.8 AND
      .message.is_counted
  );

  type Term {
    required text: str;
    required len: int16;
    total_hits: int64 {
      default := 0;
    };

    constraint exclusive on ((.text));
    index on ((.text, .len, .total_hits));
    index on (.total_hits);
  }

  type Frequency {
    # This entire table is essentially computed stats from the rest of the database.
    required community: Community;  # what community the sentence was taken from
    required term: Term;
    required min_sent_len: int16; # these will never be double digit

    required day: datetime; # the day, starting at UTC midnight, of the measured frequency
    required hits: int64;
    required multi authors: Author;
    # reportedly, the same author cannot be tracked more than once here. good.
    # required tpt: bool;  # whether the frequency was measured with toki pona sentences (score >=0.8) or all sentences

    constraint exclusive on ((.term, .community, .min_sent_len, .day));

    index on ((.day, .min_sent_len, .term));
    index on ((.day));

    # trigger update_total_hits after insert for each
    # when (__new__.min_sent_len = __new__.term.len)
    # do (
    #   update Term
    #   filter .id = __new__.term.id
    #   set {
    #     total_hits := .total_hits + __new__.hits
    #   }
    # );

    # trigger update_global_freqs after insert for each
    # do (
    #   insert GFrequency {
    #     total_hits := .total_hits + __new__.hits
    #   }
    # );
  }

  # type GFrequency {
  #   required term: Term;
  #   required min_sent_len: int16; # these will never be double digit

  #   required day: datetime; # the day, starting at UTC midnight, of the measured frequency
  #   required hits: int64;
  #   required multi authors: Author;

  #   constraint exclusive on ((.term, .min_sent_len, .day));

  #   index on ((.day, .min_sent_len, .term));
  #   index on ((.day));
  # }

}
