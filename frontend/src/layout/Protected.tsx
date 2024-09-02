import { Navigate, Outlet } from "react-router-dom";
import useAuth from "../context/useAuth";

const Protected = () => {
    const { isAuthenticated } = useAuth();

    if (isAuthenticated) {
        return <Navigate to={"/"} />;
    } else {
        return <Outlet />;
    }
};

export default Protected;
