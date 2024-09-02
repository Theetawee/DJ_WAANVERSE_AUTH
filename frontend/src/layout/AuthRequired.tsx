import { Navigate, Outlet} from "react-router-dom";
import useAuth from "../context/useAuth";

const AuthRequired = () => {
    const { isAuthenticated } = useAuth();
console.log(isAuthenticated)
    return (
        <>
            {!isAuthenticated ? (
                <>
                    <Navigate to="/login" />
                </>
            ) : (
                <>
                    <Outlet />
                </>
            )}
        </>
    );
};

export default AuthRequired;
