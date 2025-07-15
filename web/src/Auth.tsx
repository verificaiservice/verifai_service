import axios from "axios";

const server = import.meta.env.DEV ? window.location.hostname == "localhost" ? "http://localhost:12345" : "https://6v9s4f5f-12345.brs.devtunnels.ms" : "";

const get = (url: string) => axios.get(url, {
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
    }
});
const post = (url: string, data: any) => {
    if (data instanceof FormData){
        return axios.post(url, data, {
            withCredentials: true,
            headers: {
                'Content-Type': 'multipart/form-data',
            }
        });
    } else {
        return axios.post(url, data, {
            withCredentials: true,
            headers: {
                'Content-Type': 'application/json',
            }
        });
    }
}

const auth = {
    get,
    post,
    server,
}

export default auth;