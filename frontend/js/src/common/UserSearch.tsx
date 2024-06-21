import * as React from "react";
import { throttle as _throttle } from "lodash";
import { toast } from "react-toastify";
import GlobalAppContext from "../utils/GlobalAppContext";
import { ToastMsg } from "../notifications/Notifications";
import DropdownRef from "../utils/Dropdown";

export type UserSearchProps = {
  onSelectUser: (userName: string) => void;
  placeholder: string;
  clearOnSelect?: boolean;
  initialValue?: string;
};

export default function UserSearch(props: UserSearchProps) {
  // Context
  const { APIService } = React.useContext(GlobalAppContext);

  // Props
  const { onSelectUser, placeholder, clearOnSelect, initialValue } = props;

  // States
  const [newUser, setNewUser] = React.useState(initialValue ?? "");
  const [userSearchResults, setUserSearchResults] = React.useState<
    Array<SearchUser>
  >([]);

  // Refs
  const dropdownRef = DropdownRef();

  const searchUsers = async () => {
    try {
      const response = await APIService.searchUsers(newUser);
      setUserSearchResults(response.users);
    } catch (error) {
      toast.error(<ToastMsg title="Error" message={error.message} />, {
        toastId: "error",
      });
    }
  };

  const throttledSearchUsers = _throttle(async () => {
    await searchUsers();
  }, 300);

  const handleResultClick = (user: string) => {
    onSelectUser(user);
    setNewUser(clearOnSelect ? "" : user);
    setUserSearchResults([]);
  };

  React.useEffect(() => {
    if (!newUser) {
      return;
    }
    throttledSearchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [newUser]);

  return (
    <div
      className="input-group input-group-flex dropdown-search"
      ref={dropdownRef}
    >
      <input
        id="user-name-search"
        type="text"
        className="form-control"
        name="newUser"
        onChange={(event) => {
          setNewUser(event.target.value);
        }}
        placeholder={placeholder}
        value={newUser}
        aria-haspopup={Boolean(userSearchResults?.length)}
      />
      {Boolean(userSearchResults?.length) && (
        <select
          className="dropdown-search-suggestions"
          size={Math.min(userSearchResults.length, 8)}
          onChange={(e) => {
            handleResultClick(e.target.value);
          }}
          tabIndex={-1}
          style={{
            width: "100%",
          }}
        >
          {userSearchResults?.map((user, index) => {
            return (
              <option key={user.user_name} value={user.user_name}>
                {user.user_name}
              </option>
            );
          })}
        </select>
      )}
    </div>
  );
}
