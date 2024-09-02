import { createContext, useState, ReactNode, Dispatch, SetStateAction } from "react";
import { BasicAccountType } from "../hooks/types";

interface AuthContextType {
    user: BasicAccountType | null;
    isAuthenticated: boolean;
    logout: () => void;
    setIsAuthenticated: Dispatch<SetStateAction<boolean>>;
    setUser: Dispatch<SetStateAction<BasicAccountType | null>>;
    reload: boolean;
    setReload: Dispatch<SetStateAction<boolean>>;
}

export const AuthContext = createContext<AuthContextType>({
    user: null,
    isAuthenticated: false,
    logout: () => {},
    setIsAuthenticated: () => {},
    setUser: () => {},
    reload: false,
    setReload: () => {},
});

const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<BasicAccountType | null>(null);
    const [reload, setReload] = useState(false);

    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
        const stored_auth_value = localStorage.getItem("perms");
        console.log(stored_auth_value)
        if (stored_auth_value !== null) {
            return stored_auth_value === "true";
        } else {
            if (sessionStorage.getItem("perms") !== null) {
                return sessionStorage.getItem("perms") === "true";
            }
            return false;
        }
    });

    const logout = () => {
        localStorage.removeItem("perms");
        sessionStorage.removeItem("perms");
        setUser(null);
        setIsAuthenticated(false);
    };

    const contextData: AuthContextType = {
        user,
        isAuthenticated,
        logout,
        setIsAuthenticated,
        setUser,
        reload,
        setReload,
    };

    return <AuthContext.Provider value={contextData}>{children}</AuthContext.Provider>;
};

export default AuthProvider;
