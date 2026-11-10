"""Portable voice, presentation and AI settings, independent of motion identity."""
import base64
import binascii
import copy
import hashlib
import io
import re
import wave

from .container import SaveError

RETAIL = re.compile(r'retail/[a-z0-9]+(?:-[a-z0-9]+)*\Z')
CLIP = re.compile(r'(?:Character|Taunts|Enviro):(?:0|[1-9][0-9]{0,2})\Z|intro\Z|extro\Z')
CATEGORIES = ('Character', 'Taunts', 'Enviro')
DIFFICULTIES = ('easy', 'normal', 'hard')
AI_FIELDS = (
    ('Preferred_Fighting_Distance', 'Preferred fighting distance'),
    ('Attack_versus_Defend', 'Attack versus defend'),
    ('Strike_versus_Grapple', 'Strike versus grapple'),
    ('Punch_versus_Kick', 'Punch versus kick'),
    ('Strong_Punch_versus_Normal_Punch', 'Strong versus normal punches'),
    ('Strong_Kick_versus_Normal_Kick', 'Strong versus normal kicks'),
    ('Strong_Grapple_versus_Normal_Grapple', 'Strong versus normal grapples'),
    ('Shove_versus_Grapple_Move', 'Shove versus grapple moves'),
    ('Counter_Attempt_versus_Block', 'Counter versus block'),
    ('Sticky_Grapple_versus_Strike', 'Close grapple versus strike'),
    ('Env_Grapple_versus_Grapple_Move', 'Environmental versus normal grapples'),
    ('Env_Attack_Frequency', 'Environmental attacks'), ('Weapon_Frequency', 'Weapon use'),
    ('Climb_Object_Frequency', 'Climbing'), ('Running_Attack_Frequency', 'Running attacks'),
    ('Combo_Attack_Frequency', 'Combos'), ('Grapple_Defense_Proficiency', 'Grapple defense'),
    ('Strike_Defense_Proficiency', 'Strike defense'), ('Distance_Use_Proficiency', 'Distance management'),
    ('Appeal_Frequency', 'Taunting'), ('Blazin_Frequency', 'Blazin’ use'),
    ('Submit_use_Proficiency', 'Submissions'), ('Counter_Use_Frequency', 'Counter use'))
MAX_AUDIO = 8 * 1024**2
MAX_AUDIO_TOTAL = 64 * 1024**2


def require(condition, message):
    if not condition:
        raise SaveError(message)


def wav_info(raw):
    require(isinstance(raw, bytes) and 44 <= len(raw) <= MAX_AUDIO, 'Choose a WAV file of at most 8 MiB')
    try:
        with wave.open(io.BytesIO(raw), 'rb') as audio:
            channels, width, rate, count = audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes()
            require(channels == 1 and width == 2 and audio.getcomptype() == 'NONE', 'Import mono PCM16 WAV audio')
            require(8000 <= rate <= 48000 and 0 < count <= 4_000_000, 'Voice audio requires 8–48 kHz and at most 4 million samples')
            pcm = audio.readframes(count + 1)
            require(len(pcm) == count * 2, 'Voice WAV samples are truncated or inconsistent')
    except (wave.Error, EOFError) as error:
        raise SaveError('Invalid voice WAV') from error
    return dict(bytes=len(raw), sample_rate=rate, samples=count, seconds=count/rate, sha256=hashlib.sha256(raw).hexdigest())


def audio_bytes(value):
    require(type(value) is str and len(value) <= (MAX_AUDIO*4//3)+8, 'Voice clip exceeds the project budget')
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise SaveError('Invalid embedded voice clip') from error
    wav_info(raw)
    return raw


def validate(value):
    require(type(value) is dict and set(value) <= {'voice', 'intro', 'victory', 'ai'}, 'Unknown performance setting')
    for role, prefix in (('intro', 'CI_'), ('victory', 'CE_')):
        if role in value:
            require(type(value[role]) is str and re.fullmatch(prefix+r'[A-Za-z0-9]{4}', value[role]), 'Choose an original '+role+' sequence')
    if 'voice' in value:
        voice = value['voice']
        require(type(voice) is dict and set(voice) == {'preset', 'banks', 'clips'}, 'Invalid voice settings')
        require(type(voice['preset']) is str and RETAIL.fullmatch(voice['preset']), 'Choose an original voice preset')
        require(type(voice['banks']) is dict and set(voice['banks']) <= set(CATEGORIES), 'Invalid voice bank category')
        for key in voice['banks'].values():
            require(type(key) is int and 0 <= key < 65535, 'Choose an original voice bank')
        require(type(voice['clips']) is dict and len(voice['clips']) <= 767, 'Too many voice overrides')
        total = 0
        for key, clip in voice['clips'].items():
            require(type(key) is str and CLIP.fullmatch(key) and (':' not in key or int(key.split(':')[1]) < 255), 'Invalid voice clip slot')
            total += len(audio_bytes(clip))
        require(total <= MAX_AUDIO_TOTAL, 'Embedded voice overrides exceed 64 MiB')
    if 'ai' in value:
        ai = value['ai']
        require(type(ai) is dict and set(ai) == {'preset', 'tendencies'}, 'Invalid AI personality')
        require(type(ai['preset']) is str and re.fullmatch(r'cha(?:r[0-9]{4}|[0-9]{5})', ai['preset']), 'Choose an original AI profile')
        require(type(ai['tendencies']) is dict and set(ai['tendencies']) == set(DIFFICULTIES), 'AI needs all three difficulty levels')
        for slots in ai['tendencies'].values():
            require(type(slots) is list and len(slots) == 4, 'AI needs four tendency slots per difficulty')
            for edits in slots:
                require(type(edits) is dict and set(edits) <= {key for key, _ in AI_FIELDS}, 'Unknown AI tendency')
                require(all(type(n) is int and 1 <= n <= 5 for n in edits.values()), 'AI tendency values must be 1–5')
    return value


def status(value):
    result = copy.deepcopy(value or {})
    if 'voice' in result:
        result['voice']['clips'] = {key: wav_info(audio_bytes(encoded)) for key, encoded in result['voice']['clips'].items()}
    return result


def set_clip(value, target, raw):
    result = copy.deepcopy(value)
    require('voice' in result, 'Choose a voice preset before importing clips')
    if raw is None:
        result['voice']['clips'].pop(target, None)
    else:
        wav_info(raw)
        result['voice']['clips'][target] = base64.b64encode(raw).decode('ascii')
    return validate(result)
