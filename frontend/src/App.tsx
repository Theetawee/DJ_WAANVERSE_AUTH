import { createBrowserRouter, createRoutesFromElements, Route, RouterProvider } from "react-router-dom";
import RootLayout from "./layout/RootLayout";
import LoginPage from "./pages/LoginPage";

const router = createBrowserRouter(
    createRoutesFromElements([
        <Route>
            <Route path="/" element={<RootLayout />}>
                <Route path="/login" element={<LoginPage />} />
            </Route>
        </Route>,
    ])
);

const App = () => {
    return <RouterProvider router={router} />;
};

export default App;
