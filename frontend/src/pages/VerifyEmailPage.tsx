import { useState, useEffect } from "react";
import useVerifyEmail from "../hooks/useVerifyEmail";

const VerifyEmailPage = () => {
    const [counter, setCounter] = useState(10);
    const [canResend, setCanResend] = useState(false);
  const { handleVerifyEmail, isLoading, code, setCode, handleResendEmail } = useVerifyEmail();
  
    useEffect(() => {
        if (counter > 0) {
            const timer = setTimeout(() => setCounter(counter - 1), 1000);
            return () => clearTimeout(timer);
        } else {
            setCanResend(true);
        }
    }, [counter]);

    const handleResend = () => {
        if (canResend) {
          handleResendEmail();
          setCounter(10);
            setCanResend(false);
        }
    };

    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
        <form onSubmit={handleVerifyEmail} method="post">
            <div className="bg-white dark:bg-gray-800 p-8 rounded-lg shadow-lg w-full max-w-md">
                <h2 className="text-2xl font-bold text-center mb-6 dark:text-white">Verify Your Email</h2>
                <p className="text-gray-600 dark:text-gray-300 text-center mb-4">Please enter the verification code sent to your email.</p>
                <input required type="text" className="w-full px-4 py-2 mb-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white dark:border-gray-600" placeholder="Enter verification code" value={code} onChange={(e) => setCode(e.target.value)} />
                <button type="submit" disabled={isLoading} className="w-full bg-blue-500 text-white py-2 rounded-lg font-semibold hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-blue-600 dark:hover:bg-blue-700">
                    {isLoading ? "Verifying..." : "Verify Email"}
                </button>
                <div className="mt-4 text-center">
                    <p className="text-gray-600 dark:text-gray-300">
                        {canResend ? (
                            <span className="text-blue-500 cursor-pointer hover:underline" onClick={handleResend}>
                                Resend verification email
                            </span>
                        ) : (
                            `You can resend a new code in ${counter} seconds.`
                        )}
                    </p>
                </div>
          </div>
          </form>
        </div>
    );
};

export default VerifyEmailPage;
