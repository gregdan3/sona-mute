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

    multi messages := .<community[is Message];
    multi user_messages := (select .<community[is Message] filter .author.is_bot = .author.is_webhook
      and not (.container in {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821}));

    constraint exclusive on ((._id, .platform));
    index on ((._id, .platform));
  }

  type Author {
    required _id: int64;
    required name: str;
    required platform: Platform;
    required is_bot: bool;
    required is_webhook: bool;

    multi messages := .<author[is Message];
    multi user_messages := (select .<author[is Message] filter .author.is_bot = .author.is_webhook
      and not (.container in {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821}));

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
    multi tp_sentences := (select .<message[is Sentence] filter .score >= 0.8);

    constraint exclusive on ((._id, .community));
    index on ((._id, .community));
  }

  # These tables are codifying the intended querying dimension,
  # user-generated messages which are not bot activations.
  alias UserMessage := (
    select Message
      filter .author.is_bot = .author.is_webhook
      and not (.container in {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})
      #  mapona/jaki, mapona/ako, mapali/wikipesija, mamusi/ako
  );
  alias TPSentence := (
    select Sentence
    filter .score >= 0.8
  );
  alias TPUserSentence := (
    select TPSentence
    filter .message in UserMessage
  );
}
