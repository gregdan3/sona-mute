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
    multi user_messages := (select .<community[is Message] filter
      (NOT .author.is_bot OR .author.is_webhook) AND
      NOT (.container in {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821}));

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
    multi user_messages := (select .<author[is Message] filter
      (NOT .author.is_bot OR .author.is_webhook) AND
      NOT (.container in {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821}));

    constraint exclusive on ((._id, .platform));
    index on ((._id, .platform));
    index on ((.is_bot));
    index on ((.is_webhook));
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
    index on ((.container));
    index on ((.postdate));
  }

  # This table exists for the purpose of frequency analysis,
  # performing all desirable filters such that the entire alias is wanted.
  alias TPUserSentence := (
    SELECT Sentence FILTER
      .score >= 0.8 AND
      (NOT .message.author.is_bot OR .message.author.is_webhook) AND
      NOT (.message.container in {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})
      #  mapona/jaki, mapona/ako, mapali/wikipesija, mamusi/ako
  );

  alias NonTPUserSentence := (
    SELECT Sentence FILTER
      .score < 0.8 AND
      (NOT .message.author.is_bot OR .message.author.is_webhook) AND
      NOT (.message.container in {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})
  );

  type Frequency {
    # This entire table is essentially computed stats from the rest of the database.
    # I'd like to go back and add the commented out community field and tpt (toki pona taso) field,
    # but for now these are not a priority.

    required community: Community;  # what community the sentence was taken from
    required text: str;
    required length: int64;
    # if .is_word, the minimum length of counted sentences
    # if not .is_word, the length of the phrase
    # yes this is silly, but splitting would produce two nearly identical tables
    required day: datetime; # the day, starting at UTC midnight, of the measured frequency
    required occurrences: int64;
    required is_word: bool;  # whether .text is a word or phrase
    # required tpt: bool;  # whether the frequency was measured with toki pona sentences (score >=0.8) or all sentences

    constraint exclusive on ((.text, .length, .community, .day, .is_word));

    index on ((.community));
    index on ((.length));
    index on ((.is_word));
    index on ((.day));
  }
}
