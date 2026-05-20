"""Module for type hints."""

from typing import (
    Any,
    Literal,
    TypedDict,
)

from typing_extensions import NotRequired


class AppID(TypedDict):
    """Information from App ID."""

    app_id: str | None
    name: str | None


class FileSystemDict(TypedDict):
    """Information from filesystem."""

    name: str
    path: str
    size: int | None
    hostname: str
    modification_time: str | None
    access_time: str | None
    creation_time: str | None
    application: AppID


class Variant(TypedDict):
    """Represent an abstract value.

    ref: https://learn.microsoft.com/en-us/windows/win32/api/wtypes/ne-wtypes-varenum
    """

    value: Any
    value_type: str


class PropertyEntry(Variant, TypedDict):
    """A variant with a name."""

    name: str


class PropertyStoreIntValue(TypedDict):
    """Value alone without name."""

    value_size: int
    id: int
    value: str | int | None
    value_type: str


class PropertyStoreStringValue(TypedDict):
    """Value with name."""

    value_size: int
    value: str | int | None
    value_type: str
    name_size: int
    name: str


PropertyStoreValue = PropertyStoreIntValue | PropertyStoreStringValue


class PropertyStore(TypedDict):
    """Represent a property store."""

    storage_size: int
    version: str
    format_id: str
    serialized_property_values: list[PropertyStoreValue]


class PropertySheetDict(PropertyStore):
    """Property store with a header."""

    header: int


class LNKData(TypedDict):
    """Data from LNK."""

    description: str
    icon_location: str
    size: int


class LNKHeader(TypedDict):
    """LNK header."""

    guid: str
    r_link_flags: int
    r_file_flags: int
    creation_time: str | None
    access_time: str | None
    modification_time: str | None
    file_size: int
    icon_index: int
    windowstyle: str
    hotkey: str
    r_hotkey: int
    link_flags: str
    file_flags: list[str]
    header_size: int
    reserved0: int
    reserved1: int
    reserved2: int


class LNKLinkInfo(TypedDict):
    """LNK info size."""

    link_info_size: int


class LNKInfo1(TypedDict):
    """LNK with only guid info."""

    guid: str


class LNKInfo2(TypedDict):
    """LNK from automatic destination."""

    entry_id_number: str
    checksum: str
    droid_volume_identifier: str
    droid_file_identifier: str
    droid_file_timestamp: str
    droid_file_mft_seq: int
    droid_file_mac_addr: str
    droid_file_vendor: str
    birth_droid_volume_identifier: str
    birth_droid_file_identifier: str
    birth_droid_file_timestamp: str
    birth_droid_file_mft_seq: int
    birth_droid_file_mac_addr: str
    birth_droid_file_vendor: str
    hostname: str
    modification_time: str
    pin_value: int
    pin_status: Literal["Unpinned", "Pinned", "Unknown"]
    access_counter: float
    data: str


class LNKInfo2Bis(TypedDict):
    """LNK from automatic destination without entry matching."""

    entry_id_number: str


RootFolder = TypedDict(
    "RootFolder",
    {"class": Literal["Root Folder"], "sort_index": str, "guid": str},
)

VolumeItem = TypedDict(
    "VolumeItem",
    {"class": Literal["Volume Item"], "flags": str, "data": str | None},
)

FileEntry = TypedDict(
    "FileEntry",
    {
        "class": Literal["File entry"],
        "flags": str,
        "file_size": int,
        "modification_time": str,
        "file_attribute_flags": int,
        "primary_name": str,
    },
)

Internet = TypedDict("Internet", {"class": Literal["Internet"]})

ControlPanel = TypedDict(
    "ControlPanel",
    {"class": Literal["Control panel"], "item_identifier": str},
)

UsersFilesFolder = TypedDict(
    "UsersFilesFolder",
    {"class": Literal["Users files folder"]},
)

Unknown = TypedDict(
    "Unknown",
    {"class": Literal["Unknown"]},
)


class LNKTarget(TypedDict):
    """Target of an LNK."""

    size: int
    items: list[
        RootFolder
        | VolumeItem
        | FileEntry
        | Internet
        | ControlPanel
        | UsersFilesFolder
        | Unknown
    ]
    index: int


class TargetBlock(TypedDict):
    """Extra for LNK."""

    size: int
    target_ansi: str
    target_unicode: str


class SpecialFolderLocationBlock(TypedDict):
    """Extra for LNK."""

    size: int
    special_folder_id: int
    offset: int
    special_folder_name: str | None


class KnowFolderLocationBlock(TypedDict):
    """Extra for LNK."""

    size: int
    known_folder_id: str
    offset: int


class MetadataPropertiesBlock(TypedDict):
    """Extra for LNK."""

    size: int
    property_store: list[PropertyStore]


class DistributedLinkTrackerBlock(TypedDict):
    """Extra for LNK."""

    size: int
    length: int
    version: int
    machine_identifier: str
    droid_volume_identifier: str
    droid_file_identifier: str
    droid_file_timestamp: str
    droid_file_mft_seq: int
    droid_file_mac: str
    droid_file_vendor: str
    birth_droid_volume_identifier: str
    birth_droid_file_identifier: str
    birth_droid_file_timestamp: str
    birth_droid_file_mft_seq: int
    birth_droid_file_mac_addr: str
    birth_droid_file_vendor: str


class DarwinBlock(TypedDict):
    """Block for Mac."""

    size: int
    darwin_data_ansi: str
    darwin_data_unicode: str
    product_code_id: str
    feature_name: str
    component_id: str | None


class ConsolePropertiesBlock(TypedDict):
    """Information about console format in LNK."""

    size: int
    fill_attributes: int
    popup_fill_attributes: int
    screen_buffer_size_x: int
    screen_buffer_size_y: int
    window_size_x: int
    window_size_y: int
    window_origin_x: int
    window_origin_y: int
    font_size: int
    font_family: int
    font_weight: int
    face_name: str
    cursor_size: int
    full_screen: int
    quick_edit: int
    insert_mode: int
    auto_position: int
    history_buffer_size: int
    number_of_history_buffers: int
    history_no_dup: int
    color_table: int


class ShellItemIdentifierBlock(TypedDict):
    """Data for the shell in LNK."""

    size: int
    d_list: str


class TerminalBlock(TypedDict):
    """Block of data, potentially malicious."""

    size: int
    appended_data_sha256: str
    appended_data_base64: str


class LNKExtra(TypedDict):
    """Extra data for LNK."""

    ICON_LOCATION_BLOCK: NotRequired[TargetBlock]
    ENVIRONMENTAL_VARIABLES_LOCATION_BLOCK: NotRequired[TargetBlock]
    DARWIN_BLOCK: NotRequired[DarwinBlock]
    SPECIAL_FOLDER_LOCATION_BLOCK: NotRequired[SpecialFolderLocationBlock]
    KNOWN_FOLDER_LOCATION_BLOCK: NotRequired[KnowFolderLocationBlock]
    METADATA_PROPERTIES_BLOCK: NotRequired[MetadataPropertiesBlock]
    DISTRIBUTED_LINK_TRACKER_BLOCK: NotRequired[DistributedLinkTrackerBlock]
    CONSOLE_PROPERTIES_BLOCK: NotRequired[ConsolePropertiesBlock]
    SHELL_ITEM_IDENTIFIER_BLOCK: NotRequired[ShellItemIdentifierBlock]
    TERMINAL_BLOCK: NotRequired[TerminalBlock]


class LNK(TypedDict):
    """Base structure inside a jumplist."""

    status: Literal["success", "failed"]
    type: Literal["lnk"]
    modification_time: str | None
    header: LNKHeader
    link_info: NotRequired[LNKLinkInfo]
    info: NotRequired[LNKInfo1 | LNKInfo2 | LNKInfo2Bis]
    data: NotRequired[LNKData]
    extra: NotRequired[LNKExtra]
    target: NotRequired[LNKTarget]
    size: int


class ErrorLNK(TypedDict):
    """Dict used as error inside a jumplist."""

    status: Literal["failed"]
    type: Literal["error"]
    modification_time: str | None
    size: int
    data_sha256: str
    data_base64: str
    info: NotRequired[LNKInfo1 | LNKInfo2 | LNKInfo2Bis]


class BaseDict(TypedDict):
    """Abstract structure for all root dict."""

    filesystem: FileSystemDict | None
    status: Literal["success", "failed"]
    parser_version: str
    lnk: list[LNK | ErrorLNK]


class LNKDict(BaseDict, TypedDict):
    """Root dict for LNK file."""

    type: Literal["lnk"]
    modification_time: str | None


class ErrorDict(BaseDict, TypedDict):
    """Dict used when jumplist file is unparsable."""

    type: Literal["error"]
    message: str


class CustomDestinationDict(BaseDict, TypedDict):
    """Root dict for custom destinations."""

    type: Literal["custom"]
    modification_time: str | None
    version: int
    reserved0: int
    reserved1: int
    header_value_type: int
    text: str | None
    entry_count: int


class AutomaticDestEntry(TypedDict):
    """Entry inside a DestList."""

    checksum: str
    droid_volume_identifier: str
    droid_file_identifier: str
    droid_file_timestamp: str
    droid_file_mft_seq: int
    droid_file_mac_addr: str
    birth_droid_volume_identifier: str
    birth_droid_file_identifier: str
    birth_droid_file_timestamp: str
    birth_droid_file_mft_seq: int
    birth_droid_file_mac_addr: str
    hostname: str
    modification_time: str
    pin_value: int
    pin_status: Literal["Unpinned", "Pinned", "Unknown"]
    entry_id_number: str
    access_counter: float
    data: str


class AutomaticDestList(TypedDict):
    """Dest list inside Automatic destination."""

    file_version: int
    total_current_entries: int
    total_pinned_entries: int
    reserved0: float
    last_issued_id_num: int
    reserved1: int
    number_of_actions: int
    reserved2: int
    os: str
    orphan_entries: list[AutomaticDestEntry]


class AutomaticDestinationDict(BaseDict, TypedDict):
    """Root structure for automatic destination."""

    type: Literal["automatic"]
    modification_time: str | None
    dest_list_property_store: PropertySheetDict | None
    dest_list: AutomaticDestList | None


JumpEntry = (
    ErrorDict | LNKDict | CustomDestinationDict | AutomaticDestinationDict
)
