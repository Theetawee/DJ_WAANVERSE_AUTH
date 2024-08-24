import { FormEvent, useState } from "react";
import { api_url } from "./constants";
import { toast } from "react-toastify";
import { useNavigate } from "react-router-dom";

const useVerifyEmail = () => {
    const [code, setCode] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const navigate=useNavigate();

    const email = sessionStorage.getItem("email");

    const handleVerifyEmail = async (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        if (!email) {
            toast.error("Something went wrong. Please try again later.");
            return;
        }
        setIsLoading(true);

        try {
            const response = await fetch(`${api_url}/verify/email`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    email,
                    code,
                }),
                credentials: "include",
            });
            const data = await response.json();
            if (response.ok) {
                toast.success(data.msg);
                sessionStorage.removeItem("email");
                navigate("/login");
            } else {
                toast.error(data.msg[0]);
            }
        } catch {
            toast.error("Something went wrong. Please try again later.");
        } finally {
            setIsLoading(false);
        }
    };

    const handleResendEmail = async () => {
        setIsLoading(true);
        try {
            const response = await fetch(`${api_url}/resend/email`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    email,
                }),
                credentials: "include",
            });
            const data = await response.json();
            if (response.ok) {
                toast.success(data.msg);
            } else {
                toast.error("Something went wrong. Please try again later.");
            }
        } catch {
            toast.error("Something went wrong. Please try again later.");
        } finally {
            setIsLoading(false);
        }
    };

    return {
        handleVerifyEmail,
        isLoading,
        email,
        code,
        setCode,
        handleResendEmail,
    };
};

export default useVerifyEmail;
