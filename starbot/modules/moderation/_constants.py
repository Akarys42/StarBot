from starbot.models.infraction import InfractionTypes

INFRACTIONS_WITH_DURATIONS = {InfractionTypes.MUTE}
HIDDEN_INFRACTIONS = {InfractionTypes.NOTE}
UNIQUE_INFRACTIONS = {InfractionTypes.MUTE, InfractionTypes.BAN}
INFRACTION_REQUIRING_RANK = {InfractionTypes.MUTE, InfractionTypes.KICK, InfractionTypes.BAN}

INFRACTION_NAME = {
    InfractionTypes.NOTE: "note",
    InfractionTypes.WARNING: "warn",
    InfractionTypes.MUTE: "mute",
    InfractionTypes.KICK: "kick",
    InfractionTypes.BAN: "ban",
}
