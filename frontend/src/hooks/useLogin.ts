import { useState } from "react";
import { api_url } from "./constants";
import { toast } from "react-toastify";

const useLogin = () => {
    const [isLoading, setIsLoading] = useState(false);

    const [login_field, setLoginField] = useState("");
    const [password, setPassword] = useState("");

    const validateData = () => {
        if (login_field === "" || password === "") {
            return false;
        }
        return true;
    };

    const handleLogin = async () => {
        setIsLoading(true);
        try {
            const response = await fetch(`${api_url}/login`, {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    login_field,
                    password,
                }),
            });
            const data = await response.json();
            if (response.ok) {
                console.log(data);
            } else {
                toast.error("Invalid credentials");
                console.log(data);
            }
        } catch {
            toast.error("Something went wrong. Please try again later.");
        } finally {
            setIsLoading(true);
        }
    };

    const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        if (validateData()) {
            handleLogin();
        } else {
            toast.error("Please fill in all fields");
        }
    };

    return {
        handleSubmit,
        isLoading,
        login_field,
        setLoginField,
        password,
        setPassword,
    };
};

export default useLogin;
