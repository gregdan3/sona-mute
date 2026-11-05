CREATE TYPE attribute AS ENUM (
    'All',

    -- positions
    'Start',        -- starts from idx 0
    'End',          -- ends on idx -1
    'Full',         -- starts on idx 0 and ends on idx -1
    'Long',         -- in sentence with >= 4 words
    'Short',        -- in sentence with < 4 words
    'Inner',        -- does not start on idx 0 or end on idx -1

    -- parts of speech
    'Subject',      -- before li
    'Verb',         -- after li and before e
    'Object',       -- after e and before prep
    'PrepositionalObject', -- after prep
    'Predicate'     -- anything after li
    'Interjection', -- non-sentence use; probably duplicate with 'full'?

    -- more specific parts of speech
    'TransitiveVerb',   -- after li, with e
    'IntransitiveVerb', -- after li, without e
    'PrepositionalVerb' -- after li, is first prep+prep object

    -- functions
    'Content',
    'Particle',     -- duplicate with exclusive particles, but not nanpa/preps
    'Head',         -- first word in any part of speech
    'Modifier',     -- following any head in the same part of speech
    'Preposition',  -- prep itself: tawa lon tan sama kepeken
    'Preverb',      -- preverb itself: kama awen lukin alasa ken wile sona
    'Noun',         -- subject or object or prep object

    -- other
    'Unknown'       -- part or function cannot be determined
);



