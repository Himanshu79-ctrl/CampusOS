const express = require("express");
const router = express.Router();

const facultyController = require("../controllers/facultyController");

// Create faculty
router.post("/", facultyController.createFaculty);

// Provision faculty account (for existing or unlinked faculty records)
router.post("/:id/provision", facultyController.provisionFaculty);

// Get all faculty
router.get("/", facultyController.getFaculty);

// Get faculty by ID
router.get("/:id", facultyController.getFacultyById);

// Update faculty
router.put("/:id", facultyController.updateFaculty);

// Deactivate faculty
router.delete("/:id", facultyController.deactivateFaculty);

module.exports = router;