select distinct Sentence {commname := .message.community.name, content := .message.content, channe
l := .message.container} filter contains(.words, 'owe');
