module default {
  type Platform {
    required _id: int64;
    required name: str;

    constraint exclusive on ((._id))
  }

  type Community {
    required _id: int64;
    required name: str;
    required platform: Platform;

    constraint exclusive on ((._id, .platform));
  }

  type Author {
    required _id: int64;
    required name: str;
    required platform: Platform;

    constraint exclusive on ((._id, .platform));
  }

  type Sentence {
    required words: array<str>;
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
    required multi sentences: Sentence;

    constraint exclusive on ((._id, .community));
  }
}
