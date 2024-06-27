module default {
  type Platform {
    required _id: int64;
    required name: str;

    constraint exclusive on ((._id));
    index on ((._id));
  }

  type Community {
    required _id: int64;
    required name: str;
    required platform: Platform;

    constraint exclusive on ((._id, .platform));
    index on ((._id, .platform));
  }

  type Author {
    required _id: int64;
    required name: str;
    required platform: Platform;
    required is_bot: bool;
    required is_webhook: bool;

    constraint exclusive on ((._id, .platform));
    index on ((._id, .platform));
  }

  type Sentence {
    required message: Message;
    required words: array<str>;
    required score: float64;
    # NOTE: Will be pre-tokenized with the **toki pona** tokenizer,
    # and pre-cleaned by removing consecutive duplicates.
  }

  type Message {
    required _id: int64;
    required community: Community;
    container: int64;
    # if there is some further level of organization, put it here
    # e.g. discord channels, reddit flairs
    required author: Author;
    required postdate: datetime;
    required content: str;
    multi sentences := .<message[is Sentence];

    constraint exclusive on ((._id, .community));
    index on ((._id, .community));
  }
}
