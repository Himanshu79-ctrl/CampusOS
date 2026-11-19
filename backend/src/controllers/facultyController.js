const Faculty = require("../models/Faculty");
const facultyService = require("../services/facultyService");

const AUTH_SERVICE_URL = process.env.AUTH_SERVICE_URL || "http://127.0.0.1:8001";

// Create faculty with unified Auth account provisioning & rollback
const createFaculty = async (req, res) => {
  try {
    const { name, username, employeeId, email, phone, department, designation } = req.body;

    if (!name || !username || !employeeId || !email || !department || !designation) {
      return res.status(400).json({
        message: "Name, Username, Employee ID, Email, Department, and Designation are required.",
      });
    }

    const cleanEmpId = employeeId.trim().toUpperCase();
    const cleanEmail = email.trim().toLowerCase();
    const cleanUsername = username.trim().toLowerCase();

    // 1. Pre-validate uniqueness in MongoDB
    const existingByEmp = await Faculty.findOne({ employeeId: cleanEmpId });
    if (existingByEmp) {
      return res.status(400).json({
        message: `Faculty member with Employee ID '${cleanEmpId}' already exists.`,
      });
    }

    const existingByEmail = await Faculty.findOne({ email: cleanEmail });
    if (existingByEmail) {
      return res.status(400).json({
        message: `Faculty member with Email '${cleanEmail}' already exists.`,
      });
    }

    const existingByUsername = await Faculty.findOne({ username: cleanUsername });
    if (existingByUsername) {
      return res.status(400).json({
        message: `Faculty member with Username '${cleanUsername}' already exists.`,
      });
    }

    // 2. Provision Auth account on Auth Service (Port 8001)
    const authHeaders = {
      "Content-Type": "application/json",
      "Accept": "application/json",
    };
    if (req.headers.authorization) {
      authHeaders["Authorization"] = req.headers.authorization;
    }

    let authResData = null;
    try {
      const authResp = await fetch(`${AUTH_SERVICE_URL}/api/faculty/create/`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({
          username: cleanUsername,
          email: cleanEmail,
          full_name: name.trim(),
        }),
      });

      authResData = await authResp.json().catch(() => null);

      if (!authResp.ok) {
        const errMsg =
          authResData?.username?.[0] ||
          authResData?.email?.[0] ||
          authResData?.detail ||
          authResData?.message ||
          "Failed to create Auth account for faculty.";
        return res.status(authResp.status).json({ message: errMsg, errors: authResData });
      }
    } catch (authErr) {
      return res.status(503).json({
        message: `Authentication Service (Port 8001) is unreachable: ${authErr.message}`,
      });
    }

    const authUser = authResData?.user;
    const passwordSetup = authResData?.password_setup;
    const authUserId = authUser ? String(authUser.id) : null;

    // 3. Create Faculty record in MongoDB Admin DB
    let faculty = null;
    try {
      faculty = await facultyService.createFaculty({
        name: name.trim(),
        username: cleanUsername,
        employeeId: cleanEmpId,
        email: cleanEmail,
        phone: phone ? phone.trim() : "",
        department,
        designation: designation.trim(),
        authUserId: authUserId,
      });
    } catch (dbErr) {
      // 4. Compensation / Rollback: Delete newly created Auth user on failure
      if (authUserId) {
        try {
          await fetch(`${AUTH_SERVICE_URL}/api/faculty/${authUserId}/`, {
            method: "DELETE",
            headers: authHeaders,
          });
          console.log(`Rollback successful: Auth user #${authUserId} deleted.`);
        } catch (rollbackErr) {
          console.error(`Rollback failed for Auth user #${authUserId}:`, rollbackErr);
        }
      }
      return res.status(500).json({
        message: `Failed to create Faculty record in Admin database: ${dbErr.message}. Auth account was rolled back.`,
      });
    }

    res.status(201).json({
      message: "Faculty registered and account provisioned successfully",
      data: faculty,
      user: authUser,
      password_setup: passwordSetup,
    });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

// Provision Auth account and setup link for existing Faculty records
const provisionFaculty = async (req, res) => {
  try {
    const faculty = await Faculty.findById(req.params.id);
    if (!faculty) {
      return res.status(404).json({ message: "Faculty record not found" });
    }

    const authHeaders = {
      "Content-Type": "application/json",
      "Accept": "application/json",
    };
    if (req.headers.authorization) {
      authHeaders["Authorization"] = req.headers.authorization;
    }

    let authUser = null;
    let passwordSetup = null;

    // If faculty already has authUserId, generate a fresh setup link
    if (faculty.authUserId) {
      try {
        const resp = await fetch(`${AUTH_SERVICE_URL}/api/faculty/setup-link/`, {
          method: "POST",
          headers: authHeaders,
          body: JSON.stringify({ user_id: faculty.authUserId }),
        });
        const data = await resp.json().catch(() => null);
        if (resp.ok) {
          authUser = data.user;
          passwordSetup = data.password_setup;
        } else {
          faculty.authUserId = undefined;
        }
      } catch (err) {
        faculty.authUserId = undefined;
      }
    }

    // If no linked Auth account, create one now
    if (!faculty.authUserId) {
      const cleanUsername = (req.body.username || faculty.username || faculty.email.split("@")[0])
        .trim()
        .toLowerCase();

      const resp = await fetch(`${AUTH_SERVICE_URL}/api/faculty/create/`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({
          username: cleanUsername,
          email: faculty.email.toLowerCase(),
          full_name: faculty.name,
        }),
      });

      const data = await resp.json().catch(() => null);
      if (!resp.ok) {
        const errMsg =
          data?.username?.[0] ||
          data?.email?.[0] ||
          data?.detail ||
          data?.message ||
          "Failed to create Auth account for faculty.";
        return res.status(resp.status).json({ message: errMsg, errors: data });
      }

      authUser = data.user;
      passwordSetup = data.password_setup;

      faculty.authUserId = String(authUser.id);
      faculty.username = authUser.username;
      await faculty.save();
    }

    return res.status(200).json({
      message: "Faculty account provisioned successfully",
      data: faculty,
      user: authUser,
      password_setup: passwordSetup,
    });
  } catch (error) {
    return res.status(500).json({ message: error.message });
  }
};

// Get all faculty
const getFaculty = async (req, res) => {
  try {
    const faculty = await facultyService.getFaculty();

    res.status(200).json({
      data: faculty,
    });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

// Get faculty by ID
const getFacultyById = async (req, res) => {
  try {
    const faculty = await facultyService.getFacultyById(req.params.id);

    if (!faculty) {
      return res.status(404).json({ message: "Faculty not found" });
    }

    res.status(200).json({ data: faculty });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

// Update faculty
const updateFaculty = async (req, res) => {
  try {
    const faculty = await facultyService.updateFaculty(
      req.params.id,
      req.body
    );

    if (!faculty) {
      return res.status(404).json({ message: "Faculty not found" });
    }

    res.status(200).json({
      message: "Faculty updated successfully",
      data: faculty,
    });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

// Deactivate faculty
const deactivateFaculty = async (req, res) => {
  try {
    const faculty = await facultyService.deactivateFaculty(req.params.id);

    if (!faculty) {
      return res.status(404).json({ message: "Faculty not found" });
    }

    res.status(200).json({
      message: "Faculty deactivated successfully",
      data: faculty,
    });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

module.exports = {
  createFaculty,
  provisionFaculty,
  getFaculty,
  getFacultyById,
  updateFaculty,
  deactivateFaculty,
};
