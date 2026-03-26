package com.fakedetect.backend.models;

import lombok.Data;

@Data
public class LoginRequest {
    private String username;
    private String password;
}
