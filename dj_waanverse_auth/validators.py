import re
import string

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .settings import accounts_config

BAD_WORDS = [
    # Administrative terms
    "admin",
    "administrator",
    "root",
    "sudo",
    "superuser",
    "sysadmin",
    "webmaster",
    "moderator",
    "mod",
    "staff",
    "support",
    "helpdesk",
    "customerservice",
    # Common profanities and offensive terms
    "fuck",
    "shit",
    "piss",
    "cunt",
    "ass",
    "asshole",
    "bitch",
    "bastard",
    "damn",
    "hell",
    "dick",
    "cock",
    "pussy",
    "twat",
    "crap",
    "bollocks",
    "wanker",
    "bugger",
    "whore",
    "slut",
    "hoe",
    "skank",
    "thot",
    # Discriminatory or hate-related terms
    "nazi",
    "hitler",
    "kkk",
    "fascist",
    "racist",
    "sexist",
    "bigot",
    "homophobe",
    "transphobe",
    "nigger",
    "nigga",
    "chink",
    "gook",
    "spic",
    "wetback",
    "beaner",
    "kike",
    "hymie",
    "paki",
    "raghead",
    "towelhead",
    "camel jockey",
    "sand nigger",
    "fag",
    "faggot",
    "dyke",
    "homo",
    "queer",
    "tranny",
    "shemale",
    "retard",
    "mongol",
    "spastic",
    "cripple",
    # Drug-related terms
    "crack",
    "meth",
    "cocaine",
    "heroin",
    "ecstasy",
    "mdma",
    "lsd",
    "acid",
    "weed",
    "pot",
    "marijuana",
    "dope",
    "junkie",
    "stoner",
    "tweaker",
    # Violence-related terms
    "kill",
    "murder",
    "rape",
    "terrorist",
    "jihad",
    "assassin",
    "hitman",
    "bomb",
    "gun",
    "shooter",
    "sniper",
    "stabber",
    # Sexual terms
    "porn",
    "pornography",
    "xxx",
    "adult",
    "sexy",
    "horny",
    "milf",
    "dilf",
    "bdsm",
    "bondage",
    "fetish",
    "kink",
    "anal",
    "oral",
    "vaginal",
    "blowjob",
    "handjob",
    "rimjob",
    "cumshot",
    "creampie",
    "bukkake",
    # Bodily functions and anatomy
    "poop",
    "fart",
    "urine",
    "semen",
    "cum",
    "jizz",
    "penis",
    "vagina",
    "anus",
    # Religious terms (to avoid impersonation or offense)
    "god",
    "jesus",
    "christ",
    "allah",
    "muhammad",
    "buddha",
    "vishnu",
    "shiva",
    "satan",
    "devil",
    "lucifer",
    "antichrist",
    # Generic terms that could be misleading
    "test",
    "testuser",
    "username",
    "user",
    "anon",
    "anonymous",
    "system",
    "official",
    "real",
    "fake",
    "dummy",
    "temp",
    "tempuser",
    # Common weak passwords
    "password",
    "123",
    "abc",
    "qwerty",
    "letmein",
    "welcome",
    # Hacking and security-related terms
    "hacker",
    "hack",
    "phish",
    "scam",
    "spam",
    "virus",
    "trojan",
    "malware",
    # Wildcards for variations (Add * to catch variations)
    "fuck*",
    "shit*",
    "ass*",
    "bitch*",
    "cunt*",
    "dick*",
    "pussy*",
    "nigger*",
    "nigga*",
    "fag*",
    "faggot*",
    "homo*",
    "queer*",
    "porn*",
    "sex*",
    "xxx*",
    "adult*",
    "abuse*",
    "crack*",
    "drug*",
    "weed*",
    "cocaine*",
    "heroin*",
    "kill*",
    "murder*",
    "rape*",
    "terrorist*",
    "bomb*",
    "hack*",
    "spam*",
    "scam*",
    "phish*",
    # Common leetspeak substitutions
    "f*ck",
    "sh!t",
    "@ss",
    "b!tch",
    "d!ck",
    "p*ssy",
    "n!gger",
    "n!gga",
    # Controversial figures or groups
    "osama",
    "binladen",
    "isis",
    "alqaeda",
    "taliban",
    # Potentially sensitive job titles or roles
    "president",
    "ceo",
    "boss",
    "manager",
    "supervisor",
    # Brand names (to prevent impersonation)
    "facebook",
    "twitter",
    "instagram",
    "tiktok",
    "snapchat",
    "google",
    "microsoft",
    "apple",
    # Misc offensive or inappropriate terms
    "loser",
    "idiot",
    "moron",
    "stupid",
    "dumb",
    "trash",
    "garbage",
    "incel",
    "simp",
    "cuck",
    "snowflake",
    "libtard",
    "conservatard",
]


CHECK_WORDS = list(set(BAD_WORDS) | set(accounts_config["BLACKLISTED_USERNAMES"]))


def validate_username(username: str) -> tuple:
    """A function that validates the username.

    Args:
        username (str): The username to validate.

    Returns:
        tuple: A tuple containing a boolean indicating if the username is valid
            and a string containing the error message if the username is invalid.
    """
    if len(username) < accounts_config["USERNAME_MIN_LENGTH"]:
        return (
            False,
            f"Username should be at least {accounts_config['USERNAME_MIN_LENGTH']} characters long.",
        )

    if username in CHECK_WORDS:
        return False, f"Username must not contain the word '{username}'."

    # Check for allowed characters (letters, numbers, and underscores)
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username should only contain letters, numbers, and underscores."

    # Check for maximum length
    if len(username) > 30:
        return False, "Username should not exceed 30 characters."

    return True, ""


def password_validator(password, user=None):
    """
    Validates the password using Django's built-in validators and additional custom rules.
    """
    errors = []

    # Run Django's built-in password validators
    try:
        validate_password(password, user)
    except ValidationError as e:
        errors.extend(e.messages)

    # Add any additional custom validation rules
    if not any(char.isdigit() for char in password):
        errors.append(_("Password must contain at least one digit."))

    if not any(char.isupper() for char in password):
        errors.append(_("Password must contain at least one uppercase letter."))

    if not any(char.islower() for char in password):
        errors.append(_("Password must contain at least one lowercase letter."))

    if not any(char in string.punctuation for char in password):
        errors.append(
            _(
                "Password must contain at least one special character (e.g., @, #, $, etc.)."
            )
        )

    if errors:
        raise ValidationError(errors)

    return password
